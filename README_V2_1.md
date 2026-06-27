# handover-system v2.1

本版本加入資料庫相容層 `db_compat.py`，目標是讓同一份 `app.py` 可以：

- 本機未設定 `DATABASE_URL` 時使用 `site.db` SQLite。
- Render 設定 `DATABASE_URL` 時使用 PostgreSQL。

## 使用方式

1. 覆蓋專案根目錄的 `app.py`、`requirements.txt`，新增 `db_compat.py`。
2. commit / push 到 GitHub。
3. Render Web Service 新增環境變數：

```text
DATABASE_URL=<Render PostgreSQL Internal Database URL>
APP_SECRET_KEY=<你的長密鑰>
```

4. Manual Deploy → Clear build cache & deploy。

## 注意

這是 v2.1 過渡版：保留原本大部分程式邏輯，透過相容層轉接 PostgreSQL。若要做到完整長期維護版，後續建議改為 SQLAlchemy + Flask Blueprint + migration。

## v2.2 建議

- 拆分 routes/auth.py、routes/admin.py、routes/api.py。
- 拆分 services/grid.py、services/bootstrap.py。
- 將 SQL 集中在 repositories/。
- 加入資料庫 migration。
