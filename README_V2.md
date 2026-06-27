# handover-system v2

這個版本新增 `db_compat.py`，讓原本 SQLite 專案可以用 Render PostgreSQL 的 `DATABASE_URL` 啟動。

Render 環境變數：

- `APP_SECRET_KEY`: 自訂長字串
- `DATABASE_URL`: Render Postgres 的 Internal Database URL

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

注意：請把原專案的 `templates/`、`static/`、`source.xlsx` 一起保留在同一個專案根目錄。
