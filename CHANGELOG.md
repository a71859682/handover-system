# Changelog

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
