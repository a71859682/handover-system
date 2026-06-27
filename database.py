try:
    from flask_migrate import Migrate
    from flask_sqlalchemy import SQLAlchemy
except ModuleNotFoundError:
    class SQLAlchemy:  # type: ignore[override]
        def init_app(self, app) -> None:
            return None

    class Migrate:  # type: ignore[override]
        def init_app(self, app, db) -> None:
            return None


db = SQLAlchemy()
migrate = Migrate()


def init_database(app) -> None:
    import models  # noqa: F401

    db.init_app(app)
    migrate.init_app(app, db)
