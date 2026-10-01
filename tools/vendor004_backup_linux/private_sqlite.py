"""Qualification-only private SQLite build/launcher. Never installs system files."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import sysconfig
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def pins():
    return json.loads((ROOT/'pins.json').read_text(encoding='utf-8'))

def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write('\n')

def private_root(value):
    root = Path(value)
    temp = Path(os.environ['RUNNER_TEMP']).resolve()
    if (not root.is_absolute() or root.parent != temp or root.resolve() != root
            or any(c in str(root) for c in (':','\n','\r'))
            or not re.fullmatch(r'vendor004-sqlite-[0-9]+-[0-9]+', root.name)):
        raise ValueError('private_root_must_be_fresh_direct_runner_temp_child')
    return root

def private_file(path, root):
    p = Path(path)
    if p.resolve() != p or not p.is_relative_to(root):
        raise ValueError('private_file_path_rejected')
    info = p.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or info.st_mode & 0o077):
        raise ValueError('private_file_identity_rejected')
    return p

def library_path(root):
    return root/'prefix'/'lib'/'libsqlite3.so.0'

def clean_env(root, *, home=None, scratch=None):
    # Construct, never append to the caller's LD_LIBRARY_PATH/LD_PRELOAD/LD_AUDIT.
    py_lib = Path(sysconfig.get_config_var('LIBDIR')).resolve()
    if not py_lib.is_absolute() or ':' in str(py_lib) or not py_lib.is_dir():
        raise ValueError('python_libdir_rejected')
    return {'PATH': str(Path(sys.executable).parent)+':/usr/bin:/bin',
            'HOME': str(home or root/'home'), 'TMPDIR': str(scratch or root/'tmp'),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'RUNNER_TEMP': str(root.parent), 'QUAL_SQLITE_ROOT': str(root),
            'LD_LIBRARY_PATH': str(library_path(root).parent)+':'+str(py_lib)}

def mapped_sqlite(pid='self'):
    found = set()
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        if '/libsqlite3' not in line:
            continue
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or fields[5].endswith(' (deleted)'):
            raise ValueError('deleted_or_unidentified_sqlite_mapping')
        found.add(fields[5])
    return sorted(found)

def verify_mapping(paths, root, expected_sha):
    expected_path = str(library_path(root))
    if paths != [expected_path]:
        raise ValueError('private_sqlite_mapping_mismatch')
    if digest(private_file(expected_path, root)) != expected_sha:
        raise ValueError('private_sqlite_binary_hash_mismatch')

def observe(root):
    import sqlite3
    import _sqlite3
    with sqlite3.connect(':memory:') as db:
        source_id = db.execute('SELECT sqlite_source_id()').fetchone()[0]
        options = sorted(row[0] for row in db.execute('PRAGMA compile_options'))
    return {'python': list(sys.version_info[:3]), 'python_sha256': digest(sys.executable),
            'sqlite_extension_sha256': digest(_sqlite3.__file__),
            'sqlite_version': sqlite3.sqlite_version, 'sqlite_source_id': source_id,
            'sqlite_compile_options': options, 'library_paths': mapped_sqlite(),
            'library_sha256': digest(library_path(root))}

def verify_observation(actual, root, spec, binary_sha):
    verify_mapping(actual['library_paths'], root, binary_sha)
    if (actual['python'] != [3, 14, 7] or actual['sqlite_version'] != spec['version']
            or actual['sqlite_source_id'] != spec['source_id']
            or actual['library_sha256'] != binary_sha
            or 'THREADSAFE=1' not in actual['sqlite_compile_options']):
        raise ValueError('private_sqlite_runtime_identity_mismatch')

def verify_build(root, pin):
    root = private_root(root)
    if root.stat().st_uid != os.geteuid() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise ValueError('private_root_permissions_rejected')
    manifest = json.loads(private_file(root/'build.json', root).read_text())
    spec = pin['private_sqlite']
    if (manifest['source'] != spec or manifest['compile_flags'] != spec['compile_flags']
            or manifest['status'] != 'BUILT_BINARY_UNREVIEWED'):
        raise ValueError('build_provenance_contract_mismatch')
    for name, wanted in (('sqlite3.c', spec['c_sha256']), ('sqlite3.h', spec['h_sha256'])):
        if digest(private_file(root/'source'/name, root)) != wanted:
            raise ValueError('build_source_bytes_changed')
    if digest(private_file(root/'source.zip', root)) != spec['archive_sha256']:
        raise ValueError('build_archive_bytes_changed')
    actual_sha = digest(private_file(library_path(root), root))
    if actual_sha != manifest['library_sha256']:
        raise ValueError('built_library_bytes_changed')
    verify_observation(manifest['probe'], root, spec, actual_sha)
    return manifest

def require_current(root, pin):
    manifest = verify_build(root, pin)
    if os.environ.get('LD_LIBRARY_PATH') != clean_env(root)['LD_LIBRARY_PATH']:
        raise ValueError('unexpected_library_search_path')
    if os.environ.get('LD_PRELOAD') or os.environ.get('LD_AUDIT'):
        raise ValueError('unexpected_dynamic_loader_override')
    actual = observe(root)
    verify_observation(actual, root, pin['private_sqlite'], manifest['library_sha256'])
    if actual != manifest['probe']:
        raise ValueError('build_probe_process_identity_mismatch')
    return manifest, actual

def build(root, pin):
    spec = pin['private_sqlite']
    root.mkdir(mode=0o700)  # No reuse, removal or overwrite.
    for name in ('source', 'prefix', 'prefix/lib', 'home', 'tmp'):
        (root/name).mkdir(mode=0o700)
    compiler = Path('/usr/bin/gcc').resolve(strict=True)
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(root/'home'), 'TMPDIR': str(root/'tmp'),
           'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    compiler_version = subprocess.run([str(compiler), '--version'], env=env,
                                     capture_output=True, text=True, check=True, timeout=5).stdout
    with urllib.request.urlopen(spec['url'], timeout=30) as response:
        if response.geturl() != spec['url']:
            raise ValueError('source_redirect_rejected')
        raw = response.read(spec['archive_bytes']+1)
    if (len(raw) != spec['archive_bytes'] or hashlib.sha256(raw).hexdigest().upper() != spec['archive_sha256']
            or hashlib.sha3_256(raw).hexdigest().upper() != spec['archive_sha3_256']):
        raise ValueError('source_archive_pin_mismatch')
    with (root/'source.zip').open('xb') as out:
        out.write(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        # Extract only the two pinned regular source members; no extractall.
        for name, wanted in (('sqlite3.c', spec['c_sha256']), ('sqlite3.h', spec['h_sha256'])):
            member = archive.getinfo(spec['archive_root']+'/'+name)
            if member.is_dir() or stat.S_ISLNK(member.external_attr >> 16) or member.file_size > 12*1024*1024:
                raise ValueError('source_member_rejected')
            data = archive.read(member)
            if hashlib.sha256(data).hexdigest().upper() != wanted:
                raise ValueError('source_member_pin_mismatch')
            if name == 'sqlite3.c' and hashlib.sha3_256(data).hexdigest().upper() != spec['official_c_sha3_256']:
                raise ValueError('official_amalgamation_digest_mismatch')
            with (root/'source'/name).open('xb') as out:
                out.write(data)
    header = (root/'source/sqlite3.h').read_text()
    if not re.search(r'^#define SQLITE_SOURCE_ID\s+"'+re.escape(spec['source_id'])+'"$', header, re.M):
        raise ValueError('source_id_header_mismatch')
    command = [str(compiler), *spec['compile_flags'], '-o', str(library_path(root)),
               str(root/'source/sqlite3.c'), '-ldl', '-lpthread', '-lm']
    with (root/'build.log').open('xb') as log:
        log.write((json.dumps({'command': command}, sort_keys=True)+'\n').encode('utf-8'))
        log.flush()
        subprocess.run(command, cwd=root/'source', env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=120)
    binary = library_path(root).read_bytes()
    if binary[:6] != b'\x7fELF\x02\x01' or int.from_bytes(binary[18:20], 'little') != 62:
        raise ValueError('expected_x86_64_shared_library')
    for path in (root/'source.zip', root/'source/sqlite3.c', root/'source/sqlite3.h', library_path(root)):
        path.chmod(0o400)
    probe = subprocess.run([sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()),
                            'probe', '--runtime-root', str(root)], env=clean_env(root),
                           capture_output=True, text=True, check=True, timeout=10)
    actual = json.loads(probe.stdout)
    verify_observation(actual, root, spec, digest(library_path(root)))
    write_new(root/'build.json', {'status': 'BUILT_BINARY_UNREVIEWED', 'source': spec,
                                'compile_flags': spec['compile_flags'], 'command': command,
                                'compiler': str(compiler), 'compiler_sha256': digest(compiler),
                                'compiler_version': compiler_version.strip(), 'probe': actual,
                                'library_sha256': digest(library_path(root)),
                                'runner_image': {k: os.environ.get(k) for k in ('ImageOS','ImageVersion')},
                                'system_install': False, 'reviewed_binary': False})
    (root/'build.json').chmod(0o400)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('build', 'launch', 'probe'))
    parser.add_argument('--runtime-root', required=True)
    parser.add_argument('--evidence-root')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.geteuid() == 0 or sys.version_info[:3] != (3,14,7):
        raise SystemExit('Linux non-root Python 3.14.7 required')
    os.umask(0o077)
    root = private_root(args.runtime_root)
    pin = pins()
    if digest(__file__) != pin['files']['private_sqlite.py']:
        raise SystemExit('Private runtime helper pin mismatch')
    if args.command == 'build':
        build(root, pin)
    elif args.command == 'probe':
        print(json.dumps(observe(root), sort_keys=True))
    else:
        if not args.evidence_root:
            raise SystemExit('Evidence root required')
        verify_build(root, pin)
        env = clean_env(root)
        for name in ('GITHUB_OUTPUT','ImageOS','ImageVersion'):
            if name in os.environ:
                env[name] = os.environ[name]
        os.execve(sys.executable, [sys.executable, '-I', '-S', '-B', str(ROOT/'supervise.py'),
                                  '--evidence-root', args.evidence_root], env)

if __name__ == '__main__':
    main()
