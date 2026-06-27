# Database

Local development can continue using `site.db` at the project root.

`site.db` should not be committed to Git. It is a local development database and may contain machine-specific or temporary data.

Render free instances do not guarantee permanent local SQLite storage. Data stored only in the instance filesystem can be lost when the service is restarted or rebuilt.

The production database path will be improved in v2.3 and v2.4 with a SQLAlchemy-based data layer and PostgreSQL deployment flow.
