from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_app_imports():
    import app

    assert app.app is not None


def test_login_route_smoke():
    import app

    client = app.app.test_client()
    response = client.get("/login")

    assert response.status_code in (200, 302)


def test_index_route_smoke():
    import app

    client = app.app.test_client()
    response = client.get("/")

    assert response.status_code in (200, 302)


def run():
    test_app_imports()
    test_login_route_smoke()
    test_index_route_smoke()


if __name__ == "__main__":
    run()
