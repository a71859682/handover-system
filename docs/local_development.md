# Local Development Environment Baseline

## 1. Purpose

This document defines the local development environment baseline for this repository.

Its purpose is to provide a stable PowerShell 7 UTF-8 session setup so local development can avoid garbled Chinese path output, stdout encoding drift, and subprocess readability problems on Windows.

This baseline is local-only.

It does not change production behavior and does not require product-code modification.

## 2. Recommended Environment

Recommended local baseline:

- PowerShell `7.6.3+`
- Python `3.14+`
- Git `2.54+`
- Windows UTF-8 session

This combination has been validated against:

- `python -m compileall app.py tests`
- `python tests/smoke_test.py`
- representative `tools/*.py` commands

## 3. PowerShell 7 UTF-8 Session Setup

Run the following commands at the start of a local PowerShell 7 session:

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
```

This setup aligns:

- console code page
- PowerShell output encoding
- console input/output encoding
- Python stdout behavior

The goal is to keep Chinese output and Windows paths readable during local development.

## 4. Verification Commands

After applying the UTF-8 session baseline, run:

```powershell
python -c "import sys; print(sys.stdout.encoding); print(sys.getfilesystemencoding())"
git rev-parse --show-toplevel
python -m compileall app.py tests
python tests/smoke_test.py
python tools/check_site_schema.py
```

These commands verify:

- Python output encoding
- filesystem encoding
- Git path rendering
- compile chain health
- smoke chain health
- representative local tool execution

## 5. Expected Results

Expected local results:

- `chcp = 65001`
- Python stdout encoding = `utf-8`
- filesystem encoding = `utf-8`
- Chinese paths render correctly
- `python -m compileall app.py tests` = `PASS`
- `python tests/smoke_test.py` = `PASS`

Representative tool output such as `python tools/check_site_schema.py` should also show Chinese paths correctly.

## 6. Notes

- No product code change is required for this baseline.
- No workaround needs to be removed just to apply this session setup.
- PowerShell 5 may still default to `cp950` and can continue to show Chinese stdout or path rendering issues.
- If Chinese paths look garbled, first confirm that the current PowerShell 7 session has applied the UTF-8 baseline above.
- This baseline is meant to improve local developer readability and subprocess output stability, not to redefine runtime or deployment behavior.
