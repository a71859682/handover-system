# Changelog

## v2.5.0 - Dual Database Runtime Foundation
日期：2026-06-27

- 新增 `USE_SQLALCHEMY_READS` / `USE_SQLALCHEMY_WRITES`
- 新增 `config.py`
- 新增 runtime flag 檢查工具
- `settings` / `users` / `sheets` / `progress` read path 可透過 flag 切 ORM
- staging 已驗證 `USE_SQLALCHEMY_READS=true`
- 寫入仍保持 sqlite3

## v2.3.1 - Quality & CI
日期：2026-06-27

- 新增 GitHub Actions CI
- CI 自動執行 ORM checks 與 smoke test
- 新增 requirements-dev.txt
- 新增 pyproject.toml
- 新增 docs/CI.md
- 確認 CI 在 feature branch 與 main 都通過

## v2.3.0 - SQLAlchemy Foundation
日期：2026-06-27

- 新增 SQLAlchemy / Flask-Migrate / Alembic 基礎架構
- 新增 database.py 與 models.py
- 初始化 SQLAlchemy extension，但正式資料流仍維持 sqlite3
- 新增 read-only ORM services
- 新增 ORM/schema 比對工具
- 新增 Alembic baseline migration
- 鎖定 ORM / migration 套件版本
- 正式站驗證通過

## v2.2.0 - Modular Refactor & Seeded DB
日期：2026-06-27

- 將 auth/admin/sheet/api routes 拆成 Blueprint
- 將 sheet/progress 更新邏輯拆到 services
- 建立 `create_app()` app factory
- `site.db` 不再追蹤 Git
- 新增 `seeds/default_seed.json`
- 新增 seed export/import 工具
- 更新 smoke test 使用 temporary seeded DB
- `main`/`develop` 分支流程完成
