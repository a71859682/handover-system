import os
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_test_db():
    source = ROOT / "site.db"
    target = Path(tempfile.gettempdir()) / "handover-smoke-test.db"
    shutil.copyfile(source, target)
    os.environ["APP_DB_PATH"] = str(target)


configure_test_db()


def test_app_imports():
    from app import app, create_app

    assert app is not None
    assert create_app() is not None


def make_client():
    from app import create_app

    return create_app().test_client()


def test_login_route_smoke():
    client = make_client()
    response = client.get("/login")

    assert response.status_code == 200


def test_index_route_redirects_when_logged_out():
    client = make_client()
    response = client.get("/")

    assert response.status_code == 302


def test_admin_login_redirects_to_sheet():
    client = make_client()
    response = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/sheet")


def test_sheet_route_after_login():
    client = make_client()
    client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    response = client.get("/sheet")

    assert response.status_code == 200


def test_logout_redirects():
    client = make_client()
    client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 302


def run():
    test_app_imports()
    test_login_route_smoke()
    test_index_route_redirects_when_logged_out()
    test_admin_login_redirects_to_sheet()
    test_sheet_route_after_login()
    test_logout_redirects()


if __name__ == "__main__":
    run()
