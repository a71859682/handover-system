# handover-system Roadmap

## v2.1 穩定部署

- Render deployment stability
- SQLite fallback for local development
- Production startup bootstrap support

## v2.2 模組化重構

- Prepare `routes/`, `services/`, `docs/`, and `tests/`
- Add smoke tests before moving logic
- Refactor incrementally without changing behavior

## v2.3 SQLAlchemy

- Introduce SQLAlchemy models and sessions
- Keep compatibility with existing data shape
- Reduce database-specific SQL in application code

## v2.4 SQLite to PostgreSQL migration

- Provide a verified migration path from `site.db`
- Validate migrated users, sheets, tasks, units, progress, and settings
- Document rollback and backup procedures

## v2.5 照片與附件

- Add attachment upload flow
- Associate photos and files with units or issues
- Plan storage for local and hosted environments

## v2.6 PDF 報表

- Generate handover reports
- Support project, floor, unit, and task summaries
- Prepare print-friendly output

## v2.7 PWA 手機版

- Improve mobile workflow
- Add installable PWA behavior
- Prepare offline-friendly field usage

## v2.8 多建案與角色權限

- Support multiple projects
- Expand role-based permissions
- Separate administrative and field workflows

## v3.0 工程管理平台

- Evolve from handover tracking into broader construction management
- Add cross-project reporting
- Support richer operational workflows
