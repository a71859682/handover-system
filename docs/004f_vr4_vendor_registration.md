# 004F-VR4/r02 廠商待開通帳號與管理錯誤回填

廠商由 `/vendor/login` 的「廠商申請帳號（待開通）」進入 `/vendor/register`。填寫完整公司名稱、完整八碼統編、帳號、密碼及確認密碼後，成功以 HTTP 303 轉至同一 session 的成功頁。頁面明示「帳號已建立，待管理者確認，尚未開通」。沒有公開按 ID 查詢申請的入口。

## 申請規則與資料

- 公司名稱僅移除首尾空白，與已保存 VR1 `legal_name + tax_id` 精確配對；只接受唯一且 `organization_status=disabled` 的公司。浤淋有限公司沿用保存值 `00252579`。配對只確認名冊項目，不核驗申請人的身分。
- 統編是完整 ASCII 八碼字串，不轉數字、不补零、不截短。username 移除首尾空白後須為 4–64 字元，首字元為 a–z，其餘限 a–z、0–9、點、底線或連字號。不轉小寫或改写其他輸入。
- 密碼與確認值不 trim，限 12–128 字元且完全相同；拒絕 NUL。使用 Werkzeug `generate_password_hash`。伺服器將本 Blueprint 的 body／form memory 限為 16 KiB、multipart parts 限為 6；不更改其他頁面的限制。公司名最多 200 字。
- 欄位缺少／重複、檔案、query 參數、額外 ID／role／is_active 等均拒絕。CSRF 在伺服器核對；錯誤頁保留安全輸入原文字並 escaping，密碼不回填、不寫 session／URL／申請資料／日誌。既有 internal、vendor、mixed 或殘缺身分 marker 的 session 一律 403，不清除或轉換其身分。
- 成功只在 session 保存該次 username／公司／統編及更新 CSRF；不建立登入 marker。原 vendor login 仍用既有 exact lookup 並拒絕 inactive 帳號。

只新增 `vendor_registration_requests` 一張 STRICT 表：`account_id` 是一對一 INTEGER PK/FK，指向 `vendor_accounts.id`；`requested_vendor_id` 指向 `vendor_profiles.vendor_id`；另存 `submitted_company_name`、`submitted_tax_id`、`created_at`。兩個 FK 均 ON DELETE RESTRICT。它是未核驗快照，不是 membership、role、scope、批准或 AUTH global claim。`vendor_accounts.vendor_name` 僅保存配對公司名作顯示。

公開 GET 不連資料庫、不建表、不建立空 DB。POST 對注入的精確 DB 路徑使用 `file:...?...mode=rw` URI，FK 在 `BEGIN IMMEDIATE` 前 ON 並回讀。控制器明確 commit／rollback／close；服務不 import app 或建立連線，使用 caller-owned transaction 與 savepoint。當期 core／VR1／帳號 schema、名冊狀態、名稱碰撞、新表相容性、必要 DDL、顯式 `is_active=0` 的帳號 INSERT 和申請 INSERT 都在同一寫交易內。第二筆 INSERT 失敗會連新表一起回滾。既有 DB 缺失或 schema 不相容只拒絕，不 bootstrap 或修復。

## 名稱碰撞界線

同一寫交易讀 `users.username`、`vendor_accounts.username`，及完整存在的 `global_identities`／`login_identifier_aliases`／`backend_principal_mappings` registry。三表全部不存在時只做 backend 碰撞檢查；部分存在、不相容或 alias FK 關係不完整時拒絕。不建立或修改 registry。

所有 alias 狀態（active／disabled／superseded）均納入，檢查 raw alias 及保存的 normalized lookup key。原值、trim+casefold、NFKC/casefold 等價名稱保守拒絕；來源值非文字、空白或含 NUL 亦拒絕。測試所用 Python Unicode data 為 **16.0.0**，實際版本由 `UNICODE_VERSION` 暴露，測試原始輸出有記錄。本片不宣稱實作 AUTH UCD16 profile 或永續全域唯一 claim；其他帳號建立 consumer 未改。VR4 的 `BEGIN IMMEDIATE` 與既有 username UNIQUE 使同名首次請求最多一個成功。

## 管理者流程

當期 SQLite global-admin 的 VR3 `/admin/vendor-scopes` 顯示申請公司、八碼統編及 requested vendor ID，標「自行填報，尚未核驗」。管理者仍手動選廠商與帳號、明確勾選歸屬確認後保存。選定廠商不同於申請時提示差異，仍尊重既有人工判斷；不自動選定、不代勾、不搬移、不提升 owner。

申請清單放在獨立 `catalog.registration_info`；目標帳號的 `editor.registration_info` 只含展示狀態與該帳號申請，於原 fingerprint 計算後附加，不加入 fingerprint、CAS、授權或重送語義。GET 與可再提交的 POST 400 均保留目標申請公司、八碼統編及不同廠商警示，正常 escaping，不帶入其他帳號申請。缺新表或舊帳號無資料時顯示「此帳號無本片申請資料」；新表不相容或讀取失敗明示「申請資訊不可用」。既有 VR3 保存仍依原 gate 繼續。保存後組織仍 disabled、帳號 inactive、成員 pending，effective scope=0。

## r02 定向修正與驗證

本片只修正 POST 400 時 controller 有 editor、沒有 catalog，導致申請提示消失的問題。未改 controller、資料結構、保存條件或外觀。HEAD 維持 `63032a81dad65ffcd30196587386bf2a94507d8e`，分支 `feature/004f-vr4-vendor-registration`，沿用 r01 dirty 九檔；僅變更 scope service、管理模板、本測試檔及本文。

操作根為 `C:\Users\Public\Documents\004f-VR4-20260928-r02`。沿用 r01 隔離 wrapper，於 app import 前將 APP_DB_PATH、VR4_TEST_ROOT／VR3_TEST_ROOT、TEMP／TMP 與 pycache 指向本片新子目錄；外部 backend 停用，SQLite containment／網路／PostgreSQL guards 先安裝。只新建 synthetic SQLite，原始回應、argv、filter、child／外層 exit 與 streams 留存 Record。

實際 Flask 回歸先在未修產品上重現提示缺失（同／不同廠商兩個 subtests，child／外層 exit 1），修正後同方法通過。從 400 HTML 解析完整表單，確認確認勾選、工地／工項、理由及 snapshot 保留；錯誤時 schema／rows 及 DB 原 bytes 不變。修正理由重送 303 後仍 inactive／disabled／pending、effective=0，申請快照仍指向原申請廠商。

定向執行 8 個 VR4 方法，均通過；不是完整重跑 32 項。每次使用 `python -m unittest discover -s tests -p test_vendor_registration.py -v`，搭配下列各別 `VR4_TEST_FILTER`：

- `test_admin_post400_preserves_target_request_and_mismatch`
- `test_admin_post400_uses_only_target_request`
- `test_admin_absent_supplement_and_legacy_account_unchanged`（缺表及有表但目標無申請）
- `test_admin_incompatible_supplement_explicit_unavailable_can_save`
- `test_admin_mismatch_warns_manual_choice_can_be_saved`
- `test_display_data_does_not_change_fingerprint_cas_or_replay`（含 GET／400 escaping）
- `test_end_to_end_manual_confirmation_still_pending_zero_effective`
- `test_admin_current_global_role_gate_no_request_leak`

另以操作根 `select_vr3.py` 選取既有 VR3 首次保存、重送不寫入、錯誤回填、stale revision 與兩個 client 首次保存競爭共 5 項，全數通過；只替換 test loader 的選取，原 app-import 前隔離流程與 repo VR3 測試未改。改動的兩個 Python 檔案 compile 與 `git diff --check` 以 Record 真 exit 為準。

最高狀態為 `VR4_WARNING_PRESERVED_AND_TESTED / PENDING_EXTERNAL_REVIEW`。沒有可達且版本明確的隔離預覽；`BUILTIN_BROWSER_INTERACTION=PENDING_REACHABLE_VR4_PREVIEW`，此處交付實際 Flask 回應，不宣稱瀏覽器互動或視覺 PASS。正式 runtime／live／部署、外審接受、成功 Second Copy 與 commit 均尚未完成。

## r01 隔離驗證與歷史結果（非 r02 重跑）

執行根為 `C:\Users\Public\Documents\004f-VR4-20260927-r01`。`run_check.py` 每次產生全新 `check-...` 子目錄，設定 APP_DB_PATH、DATABASE_URL 空值、停用 SQLAlchemy read/write／compare／dual-write，並將 TEMP/TMP/TMPDIR、pycache 放在該子目錄。VR4／VR3 wrapper 在子程序 app import **以前**安裝 SQLite containment、network 與 PostgreSQL guards。所有 SQLite fixture 均於本轮根新建；未使用既有 DB。

必要命令：

```text
python -m unittest discover -s tests -p test_vendor_registration.py -v
python -m unittest discover -s tests -p test_vendor_scope_admin.py -v
python -m py_compile app.py routes/vendor_registration.py services/vendor_registration_service.py services/vendor_scope_admin_service.py tests/test_vendor_registration.py
git diff --check
```

VR4 設 `VR4_TEST_ROOT`，VR3 設 `VR3_TEST_ROOT`，皆指向該次新子目錄。修正後可用 `VR4_TEST_FILTER=<test_method_name>` 只重跑受影響案例；不設則完整執行。實際命令、filter、真 exit 及原始 stdout/stderr 由本輪 Record 保存。

本輪 VR4 30 個不同案例均已有通過證據：初跑 29 個中 28 個通過，1 個測試準備的 DROP 被 FK 阻止；修正後該案例單獨通過。唯讀審查發現錯誤回填截短識別輸入，已修正，新增保留原值案例及既有 escaping 案例均通過。沒有改 VR3 原測試；VR3 35 個 child tests＋1 wrapper 完整通過。涵蓋完整註冊→inactive login 拒絕→人工 VR3 保存、前導零、欄位／session／CSRF／escaping、所有 alias 狀態、缺失／不相容 schema、同名並發、第二 INSERT 回滾、CAS／重送不受申請資料影響。compile／diff 結果以 Record 真 exit 為準。

現有 Chrome 已在新建 loopback fixture 擷取桌面 1280×900、窄版 390×844 的註冊／錯誤／成功／管理申請與 ALL/SELECTED 互動畫面，並完成一次人工確認保存。只准 loopback server bind；fixture app 的 outbound network／外部 backend 均阻止。截圖及 DOM 觀測在 Record，狀態為 `CAPTURED_PENDING_EXTERNAL_VISUAL_REVIEW`，不宣稱視覺 PASS。原有 base.html 在未選工地時顯示 HTML entity 文字，未擴至九檔外修正；本次流程可操作。

r01 當時最多 `VR4_INACTIVE_REGISTRATION_IMPLEMENTED_AND_TESTED / PENDING_EXTERNAL_REVIEW`，外審要求本次警示修正。正式 runtime 範圍接線、開通、既有 DB migration、live、部署、ChatGPT 外審接受與 Second Copy 均未完成。沒有 commit／push／merge／deploy、安裝、Render／SSH／PostgreSQL 連線。


## 004F-VR4-UX/r01：公司點選與繁中登入（2026-09-28）

本節是目前產品契約，取代上方歷史 r01/r02 的手填公司／統編及 GET 零 DB 存取敘述；歷史測試與預覽證據原文保留，不代表本輪重跑或接受。本輪限本機實作及定向隔離測試，最高結果為 `UX_IMPLEMENTED_PENDING_EXTERNAL_REVIEW`。

公開申請改為有明確 label 的原生公司 select，可使用鍵盤及手機原生選項。預設「請選擇公司」，不預選第一家。選項顯示 display_name 與 legal_name，相同時僅顯示一次；同名選項追加完整穩定 vendor_id 識別，均由 Jinja 自動 escaping。使用者不必知道完整公司名或統編。只列 disabled 且能通過原公司名長度規則的名冊公司，active／retired 不可申請；公司選擇僅聲稱歸屬，尚未核驗，不授權。

GET 現在只開已存在 DB 的 `mode=ro` URI，先開 foreign_keys／query_only，再明確 BEGIN；呼叫既有 core guard 與 roster.list_profiles 的 schema／profile-organization 一致性檢查，最後 rollback／close。傳給表單的公司投影嚴格只有 vendor_id、display_name、legal_name；tax_id、aliases、source、users 或完整 profile JSON 不送入模板。不 initialize／migrate／建 DB／寫入名冊。正常空名冊顯示中文說明並停用 select／送出；缺 DB、名冊不可讀或不相容回 503，不偽裝為空名冊。沒有新增公開搜尋 API 或前端框架。

公開 POST exact shape 為 vendor_id、username、password、confirm_password、csrf_token，各一個；缺欄、重複、額外欄、舊 company_name／tax_id shape、query 及上傳檔案均拒絕。原 session CSRF、既有身份拒絕及 16 KiB body／form memory／6 parts 界線保留。selector adapter 於原 BEGIN IMMEDIATE 交易內重新讀取合格公司，伺服器取回 legal_name 與八碼字串 tax_id；保留 `service.FIELDS`、validate、register 的既有 canonical contract、跨表與所有 alias 狀態碰撞檢查、registry/backend guard、savepoint 及兩筆 INSERT 回滾。未複製 username 或碰撞驗證。GET 後公司刪除、資格改變或未知 ID 拒絕且不寫。成功仍 303 PRG，receipt 使用當時 canonical 資料及前導零，帳號 inactive、requested_vendor_id 正確，不自動登入。

400 保留仍有效的公司選項與完整 username，密碼欄永遠空白。已失效選項明示重新選擇並回到空白提示，不換成另一家公司。成功頁與管理頁統一說「申請人提供的公司歸屬，尚未核驗」，適用歷史手填紀錄，不回填或宣稱歷史紀錄由選單產生。管理模板僅換文案，互動與權限不改。

廠商登入頁 title、標題、帳密標籤、登入／登出、已登入提示及申請入口使用繁中。wrong／unknown／inactive 共用「廠商帳號或密碼錯誤，或帳號尚未開通」。app.py 只改該字串，verify_vendor_account、session.clear、set_vendor_session、redirect 全部保留，內部 /login 與其他頁面不改。

### 隔離預覽登入指引與 fixture 責任

已唯讀核對原 source 的 `preview/vr4_20260928_r01/entry.py`、`fixture.py` 與 README。隔離預覽使用獨立 SQLite 與合成公司／工地／工項；沒有複製真實 users，原管理員帳密因此不能使用，並不是缺少 DB。管理者從 `/login` 使用專用 username `vr4.preview.admin`；密碼由遠端 Render `VR4_PREVIEW_ADMIN_PASSWORD` 提供。請由有權管理該 secret 的人依既有安全方式取得，不在 README 硬編碼或複製帳密。本輪未讀取、回顯、變更遠端 secret，也未連真實 DB 或部署。廠商申請入口為 `/vendor/register`，登入入口為 `/vendor/login`；新申請帳號尚未開通，不能登入。

合成 fixture 僅供確認申請、管理員人工核驗提示與 pending 設定；選擇另一廠商、勾選範圍、理由空白的 POST 400 應保留原選項、勾選、申請提示與安全欄位，且 DB 不變。更正理由後 303 仍是 pending／inactive／disabled，effective scope=0。本輪以正常 /login、即時產生密碼及正常 hash 的 Flask client 驗證此路徑，不偽造 admin session 或替換 auth。

正式啟用前，由預覽資源負責人盤點並關閉本預覽服務、清除其暫時 admin／測試廠商／合成 SQLite／臨時 secret 與瀏覽器登入狀態；本機 fixture 由本輪執行者依另行清除授權處理，保留已接受的 Record。不要對正式 DB 執行測試資料清除 SQL，不把 fixture、預覽 entry 或密碼帶入產品 commit。預覽 README 的本輪補充放在本次 Record `evidence/PREVIEW_LOGIN_README.md`，歷史 README 不改。

### 本輪驗證及交付邊界

測試 wrapper 在 app import 前固定新 fixture APP_DB_PATH；DATABASE_URL／DUAL_WRITE_TABLES 清空，SQLAlchemy reads/writes、USERS_READ_COMPARE 及 dual-write 開關均 false。SQLite containment、網路／PostgreSQL／source.xlsx guard 先安裝。只以 `VR4_TEST_FILTER=<單一精確方法名>` 呼叫現有隔離 worker，不啟動完整歷史 suite、H9 或預覽 smoke；明列案例、原始 streams、修正及真 exit 以本輪 Record 為準。測試密碼與 session key 即時合成，安全值與 DB 不交付。changed Python compile 的 pycache 留在 repo 外。

本輪不修改 Git index／refs，不 stage／commit／push／merge，不寫 source repo 或歷史 Record，不部署、不安裝、不啟動子代理。外審接受、成功 SecondCopy、受控產品 commit、preview 整合／部署及內置瀏覽器驗收須分別處理；本機 Flask 測試不是 browser PASS。
