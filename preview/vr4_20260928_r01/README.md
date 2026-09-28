# 004F-VR4-UX-PREVIEW/r01 預覽交接

本輪上限：**PREVIEW_INTEGRATION_READY_PENDING_EXTERNAL_REVIEW**。
DEPLOYMENT=NOT_STARTED；BROWSER_REVIEW=PENDING；EXTERNAL_REVIEW=PENDING；SECOND_COPY=PENDING。
本機 HTTP/HTML smoke、CLI exit 0 與 ZIP 都不是產品 PASS，也不是 browser pass。
產品 UX commit 已由前輪外審接受並成功 SecondCopy；本輪預覽整合仍須獨立外審及 SecondCopy。

## 來源與目前入口

- Repository：`https://github.com/a71859682/handover-system.git`。
- 產品 baseline：`a0eb5d2055ce047ce2eb5c862b6457853daa6643`；tree：`197dea7c0bef14a08cebfeacea26f31f995db1d3`；227 tracked。
- 新 detached repo：`C:\Users\Public\Documents\004f-VR4-UX-PREVIEW-20260928-r01\repo`。
- 僅新增 `preview/vr4_20260928_r01/{README.md,entry.py,fixture.py,smoke.py}`。
  entry 保留原 bytes；fixture 只改身份、baseline、Windows/Render roots。package 路徑保留為相容既有 Start command，沒有執行歷史 RUN。
- 原產品 `C:\Users\Public\Documents\004f-VR4-UX-20260928-r01\repo` 與舊 preview source
  `C:\Users\Public\Documents\004f-VR1-20260927-r01\repo` 均只讀。
- Record：`I:\公司web\record\product-mainline\vendor-id\004f\vr4-ux-preview-20260928-r01`。

真產品入口：`/vendor/register` 廠商申請、`/vendor/login` 廠商登入、`/login` 內部登入、
`/admin/vendor-scopes` 內部管理。`/preview/version` 是診斷及 health endpoint，不是產品首頁。

沿用既有隔離 Render service。以下是授權提供的交接狀態，本輪沒有遠端查詢：

| 項目 | 值 |
| --- | --- |
| workspace | `tea-d8vmr4ok1i2s73etn1tg` |
| service | `srv-dasvh9npn0mc73a97mrg` |
| name | `handover-vr4-preview-20260928-r01` |
| URL | `https://handover-vr4-preview-20260928-r01.onrender.com` |
| 現有 branch | `preview/004f-vr4-20260928-r01` |
| 現有 commit／舊 preview source HEAD | `96270326607481909fff624dddbe3a4d8c567907` |
| autoDeploy | `no` |
| 待建立新 branch | `preview/004f-vr4-ux-20260928-r01` |

既有 URL 現在仍顯示舊版；本輪沒有上線。實際 deployed SHA、preview identity、baseline、
fixture 證明一致之前，不能當作本輪新版入口。新 preview commit 尚未建立，不得捏造 SHA。

## 後續受控部署與 branch 缺口

1. 本輪外審接受及成功 SecondCopy 後，另開受控 gate 才建立上述新 branch、commit、push；舊 refs 不回寫。
2. connector 沒有更新 branch／指定 commit 功能，不能只 trigger 舊 branch 部署。
   後續在受支持 Render Dashboard 的既有 service Settings / Build & Deploy / Branch 修改為新 branch，保存並確認 autoDeploy=`no`。
   本輪不操作 Dashboard 或 connector，不另建服務規避，不變更正式服務。
3. 同一服務 Environment 切換下面的新身份與 DB 根，維持既有 secrets；不接正式 DB、磁碟或 env group。
4. 核對 push 的新 preview commit 後手動 deploy，核對部署詳情的實際 deployed SHA 與 Render 注入的 `RENDER_GIT_COMMIT`。
   產品 baseline 不等於新 preview commit。核對 `/preview/version` 後才開新版入口及內置瀏覽器驗收。
5. free `/tmp` 可能於 redeploy／冷啟動重新建立 fixture。browser 驗收必須同 boot／同 fixture，identity 改變不能混證。

Build 保持（本輪不安裝）：

```sh
python -m pip install -r requirements.txt
```

Start 保持（一 worker、一 thread，不 preload/debug/reload）：

```sh
gunicorn preview.vr4_20260928_r01.entry:app --workers 1 --threads 1 --bind 0.0.0.0:$PORT --timeout 120 --access-logfile /dev/null --error-logfile - --log-level warning
```

Health `/preview/version` 僅為診斷。不得改用產品 `app:app` 跳過隔離。
本輪使用已安裝的本機 Python／套件，未驗證 Linux/Gunicorn。

| 非秘密 Environment | Render 值 |
| --- | --- |
| `VR4_PREVIEW_MODE` | `004F-VR4-UX-PREVIEW/r01` |
| `VR4_PREVIEW_RUNTIME` | `RENDER` |
| `VR4_PREVIEW_ROOT` | `/tmp/004f-vr4-ux-preview-20260928-r01` |
| `APP_DB_PATH` | `/tmp/004f-vr4-ux-preview-20260928-r01/fixture.sqlite3` |
| `VR4_PREVIEW_ADMIN_USERNAME` | `vr4.preview.admin` |
| `PYTHONDONTWRITEBYTECODE` | `1` |
| `DATABASE_URL` | 明確存在的空字串 |
| `DUAL_WRITE_TABLES` | 明確存在的空字串 |
| `USE_SQLALCHEMY_READS` | `false` |
| `USE_SQLALCHEMY_WRITES` | `false` |
| `USERS_READ_COMPARE` | `false` |
| `DUAL_WRITE_ENABLED` | `false` |
| `DUAL_WRITE_DRY_RUN` | `false` |
| `DUAL_WRITE_STRICT` | `false` |
| `FLASK_DEBUG` | `0` |
| `FLASK_TESTING` | `false` |

`PORT`、`RENDER_GIT_COMMIT` 由 Render 提供，後者為 lowercase 40-character SHA。
Python runtime 與其餘設定維持現有服務配置，後續部署 gate 再確認平台相容性。

專用遠端帳號是 **`vr4.preview.admin`**，密碼來自該服務 Environment 的
`VR4_PREVIEW_ADMIN_PASSWORD`；原系統帳密不適用。
`APP_SECRET_KEY`／`VR4_PREVIEW_ADMIN_PASSWORD` 留現有 service secrets；本輪不讀取、輸出、複製或更動。
密碼須 24–128 字元、至少 12 種字元；APP secret 須 43–256 字元、至少 16 種字元且不同於密碼，
使用密碼學強隨機生成。沒有 fallback secret；缺／弱值在 app import 前拒絕。
同 fixture 重啟須用相同管理員身份／密碼，不會默默重設或輪替。

## 申請操作與部署後 browser 驗收

這是有**獨立 SQLite DB** 的隔離預覽，不是沒有 DB。
公司名冊是合成資料：「預覽合成甲有限公司」、「預覽合成乙有限公司」。
工人只需點選所屬公司，不必知道／手填公司全名與統編；選公司只是聲稱歸屬，仍待 admin 核驗。

1. 讀 `/preview/version`，核對新 identity、產品 baseline、實際 deployed commit、`synthetic=true`、boot ID、fixture instance。
2. 匿名進 `/vendor/register`：native select 預設空，點選甲公司、輸入新帳號及臨時強密碼。
   表單只有 `vendor_id/username/password/confirm_password/csrf_token`，沒有 `company_name/tax_id`。
   vendor_id 取自此頁 option，不猜值，保留正常 CSRF。
3. 先用不一致的兩次密碼驗證 400：公司與帳號保留，兩個密碼欄清空；再更正提交，成功 303 PRG。
   顯示「帳號已建立，待管理者確認，尚未開通。」與 server canonical 公司及保留前導零的統編。
   原 requested_vendor_id 為甲；帳號 inactive，沒有 effective authorization。
4. `/vendor/login` title、帳號／密碼 label、登入 button、申請連結皆繁中。
   inactive 帳號使用真密碼仍為一般中文錯誤，不獲廠商身份；本輪不重跑產品 wrong/unknown 完整矩陣。
5. 專用 admin 正常 `/login` 後到 `/admin/vendor-scopes`，選乙公司與剛申請帳號，核對跨公司警示。
   確認會員；site 101 SELECTED 302+303、site 102 ALL。觀察 reason 空白真 POST400 時，
   只略過 browser required-field 阻擋，保留原 CSRF／signed snapshot。
6. 400 保留公司、帳號、提示、全部選擇／勾選及原 CSRF／snapshot；固定 readonly summary 不變。
   更正 reason 後 303：account inactive、org disabled、membership pending、configured3/effective0。
   原申請甲公司不被乙覆寫。

`/preview/fixture-state` 僅供正常 internal admin 讀固定安全投影；匿名 403，無 caller SQL/path/filter，POST 不支援。
本機 smoke 將兩個 400 前後的完整 DB 原 bytes 只留記憶體比較，不輸出 DB 或 DB fingerprint；
safe summary fingerprint 只代表固定安全投影。另做一次同 fixture 重啟，驗證 boot 不同、fixture 相同、資料及正常 admin 登入保留。
HTTP/HTML 解析與 cookiejar 不執行 browser JS，不能稱 browser pass。

## 保留隔離、本機執行與後續清理

保留 import 前驗證、SQLite audit、拒絕 repo `source.xlsx`、symlink/junction/hardlink 排除、
exclusive startup lock、unknown/partial fixture／orphan journal 保留拒絕及不重設。
正常產品 schema/bootstrap/hash、roster 服務產生兩家 disabled 合成公司、兩個 active 工地、三張表與六工項。
預設 bootstrap 工地 inactive；預設 admin 保留名字、防止 bootstrap 重建，改為 member 與廢棄隨機密碼，admin/admin 禁用。
原登入、申請、admin route、交易、授權、CSRF、signed snapshot 保留；不 mock current_user/session/response。
summary 使用 `mode=ro`／`query_only`，重新驗證 admin；無 reset/activation/admin bypass/public SQL/帳密 API。
`/admin/users`、`/admin/table`、`/api/reset-sheet` 維持 404。

本輪執行命令（結果見 Record；不是授權重跑歷史 gate）：

```powershell
python -B -m preview.vr4_20260928_r01.smoke
```

新資料僅在 `C:\Users\Public\Documents\004f-VR4-UX-PREVIEW-20260928-r01\run-<uuid>`，
其中 `fixture\fixture.sqlite3` 是全新實例；不搬舊 DB／instance。
14 個必要 pre-import probes：錯 mode、舊 root、repo DB、`/var/data/site.db`、任意 DB、DATABASE_URL、
DUAL_WRITE_TABLES、缺／弱 APP_SECRET_KEY、四個寫入 flags、unknown DB 不覆蓋。
每例證明 app import 未嘗試；Windows `/var/data` 在絕對路徑檢查就拒絕。
未執行舊 smoke、H9、歷史 RUN 或 `tests/test_vendor_registration.py`。

即時強隨機密碼與 APP secret 只留記憶體及子 process env，不進命令參數。
事件從來源只產生安全欄位；HTTP body/header、cookie/session、CSRF/snapshot、密碼／hash 不捕獲，沒有先洩漏再刪改。
只用本輪 process handle 停止自建 listener，記錄真 PID／exit／port closed。失敗目錄保留。
fixture DB／unknown probe DB 不進 Record、Git、ZIP；compile 不寫 repo pycache。
產品 app/templates/routes/services/tests/docs、requirements、Procfile 全數不改，不重跑產品測試。

同 fixture restart 不 reset；free `/tmp` redeploy／冷啟動可能新建 fixture，不同 boot／instance 證據不可混用。
臨時管理員與合成申請帳號正式啟用前須刪除；另行授權後只清理此隔離服務／新 root，**本輪不清理**。
沒有對正式 DB 做帳號 SQL。本輪無 Git add/commit/push/merge/reset/amend/clean、worktree 操作、refs/index/config 寫入，
也沒有遠端連線、部署、browser 操作或新工具安裝。UX/r01、UX-COMMIT/r01 保持封閉。
