import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="handover-smoke-test-"))
TEST_DB_PATH = TEST_DB_DIR / "site.db"


def configure_test_db():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    os.environ["APP_DB_PATH"] = str(TEST_DB_PATH)


configure_test_db()


def load_app_module():
    from app import app, bootstrap, create_app

    bootstrap()
    return app, bootstrap, create_app


def test_app_imports():
    app, _, create_app = load_app_module()

    assert app is not None
    assert create_app() is not None


def make_client():
    _, _, create_app = load_app_module()

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
