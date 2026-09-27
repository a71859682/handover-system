# 004F-VR3/r01 廠商待開通設定

本片提供已註冊的 `/admin/vendor-scopes` 頁面，從「成員管理 → 廠商待開通設定」進入。管理者可明確選擇已保存廠商與既有未啟用帳號，設定工地和工項、保存並重新開啟核對。保存結果仍是「待開通，尚未生效」。

## 操作與資料前提

必須是當期 SQLite `users.role='admin'` 的 internal 帳號。舊 session role、工地管理角色、vendor session、混合 identity 均不能代替此資格。頁面不依 `current_site_id` 換掉目標、不修改內部工地權限。

1. 明確選擇公司（名稱、完整八碼統編、vendor ID）及既有帳號（username、account ID）。名稱只作標籤；不以 `vendor_name` 推算歸屬。
2. 只有帳號 `is_active=0` **且** 廠商 `organization_status=disabled` **且** membership 尚無歷史／唯一同廠商 `pending` 才能保存。首次須勾選歸屬確認，新 membership 固定為 `member + pending`。原有 owner/member role 不會變更。
3. 首次所有工地不勾選。勾选工地預設 ALL；ALL 涵蓋該工地本廠商在所有合格表格下的工項，也涵蓋日後新增且符合完整交集的工項。切換 SELECTED 後，以「表格名稱／工項名稱」及穩定 IDs 勾選；沒有額外表格授權層。
4. SELECTED 空集合是零工項；ALL 必須送出空 task IDs。取消工地只刪除此成員 scope，不刪共用 assignment/binding。保存替換整份工地集合，全部不勾選即清空此成員配置。
5. 填寫 1–500 字理由，按「儲存待開通設定」。成功為 HTTP 303，重開後可核對 revision、保存的工地／模式／task IDs 與配置工項數。無可配置帳號時明示「尚無待開通帳號」，不製造帳號。

核心四表與已保存 VR1 兩表是前提。GET 使用唯讀 URI 與 `query_only`，不初始化 schema、不建立關係、不保存預設；資料庫檔不存在也不新建。VR2 四表全部不存在時可以瀏覽，經授權 POST 才在同交易呼叫既有 initializer；部分存在或不相容回覆 503。

候選工項只讀 VR1 `list_profiles`／`list_task_assignments` 的穩定歸屬及當期 site/sheet/task 關係。未歸屬工項排除並顯示待處理數量。已啟用帳號／組織或非 pending 成員只顯示不能修改的原因。

交接示例的浤淋統編為 `00257979`，但接受基線的 VR1 原件保存 `00252579`，並保留原始／補充／verified 來源。此頁原樣顯示保存值，不改 VR1 名冊或把範例硬編成資料；八碼前置零完整保留。

## 保存、快照與拒絕

Controller 在 fresh request connection 上啟用並讀回 FK，POST 使用 `BEGIN IMMEDIATE`。當期 DB admin 驗證、只讀核心 classifier、VR1／VR2 前提、關係歷史檢查、必要 DDL、新 membership／links、VR2 scope／event 皆在同一交易。服務另有 nested savepoint；任何例外回滾該保存，controller 再 rollback／close。GET／POST 不呼叫核心 ensure 來補 schema。

新 membership、assignment、binding 都由伺服器產生 UUID4。已有唯一、完整吻合的 active links 可沿用；inactive、衝突、多世代、跨工地／廠商不一致，以及被其他 row 引作 predecessor 的 successor 歷史皆拒絕，不復活、不換代。新核心 row 的 created／updated provenance 均使用 `internal_user`、當期 actor ID、理由、固定 VR3 source 與共同 correlation UUID。只為勾選工地與本廠商候選工項實際所在 sheets 準備 binding。

準備後的最終資格透過 VR2 公開管理查詢重用既有 `_eligible` 完整交集，再由原 `save_scopes`／`preview_scopes` 保存及核對。VR2 原 save／preview／resolver 行為未改；新增兩個只讀公開管理介面：`admin_schema_state`、`list_admin_eligible_tasks`。

編輯 token 有 30 分鐘有效期，簽署 actor、session CSRF、目標 vendor/account 與完整管理快照 fingerprint。快照涵蓋 membership／links IDs 與不存在狀態、predecessor／successor、revision、當期選項與已保存 scope。POST 重核；目標啟用、管理者降權、關係換代、工項移動或歸屬變更均不能由舊頁覆蓋。

失效的完整舊選項不會靜默濾掉：HTTP 409 顯示未保存輸入與重新載入入口；已保存失效選項會停止編輯，待資料前提處理後重新確認。一般表單錯誤 HTTP 400，保留可理解的選擇與理由；CSRF／actor 失敗 HTTP 403 且不帶帳號、公司或工項明細。HTML 使用 Jinja escaping。

同一 session 保留最後一次成功請求的有界 receipt。30 分鐘內、相同完整內容、同 actor 且當期保存後快照未變的重送可回報原成功，零新增 row/event/revision。不同內容或其他舊快照是 409；沒有 receipt 不猜測成功。新頁的相同 scope 保存另沿用 VR2 idempotence。此機制不新增審計表或全域框架。

## 驗證與執行方式

僅使用全新隔離 SQLite 測試資料。正式執行環境在本輪操作根建立 `VR3_TEST_ROOT`，並在任何 app import 前設定：`APP_DB_PATH` 指向該根、`DATABASE_URL=''`、所有 SQLAlchemy read/write／compare／dual-write flags 為 false、`DUAL_WRITE_TABLES=''`、TEMP/TMP/TMPDIR 指向新隔離根；封鎖網路與 PostgreSQL 入口並限制 SQLite 到新根。不使用正式 DB。

```text
python -m unittest discover -s tests -p test_vendor_scope_admin.py -v
python -m unittest discover -s tests -p test_vendor_access_service.py -v
python -m py_compile app.py routes/vendor_scope_admin.py services/vendor_scope_admin_service.py services/vendor_access_service.py tests/test_vendor_scope_admin.py
git diff --check
```

VR3 discover 在父程序收集一個隔離包裝測試，實際 Flask／服務行為測試在子程序執行並輸出每項結果與實際件數。原 VR2 27 項回歸檔案保持原 bytes。實際命令、子程序原輸出、真 exit、失敗診斷、隔離計數及終版結果以本輪 Record 的 `evidence/checks`／`REPORT.md` 為準。

涵蓋實際 Flask GET → 明確選擇 → POST → GET、導覽、HTML controls／escaping、唯讀 GET、完整集合替換、跨 vendor/site 工項拒絕、當期身分、CSRF、舊 revision／世代／資料變更、兩個同時首次 POST、準備後及 event 後故障全回滾、核心 guard、保存後三狀態與 effective scope=0、受保護資料不變。測試客戶端不是瀏覽器或 live 驗收。

`VISUAL_BROWSER_NOT_RUN`：本輪未執行桌面／窄畫面瀏覽器渲染。模板做人工原碼可讀性檢查，HTML 與表單以真實 Flask test client 檢查。原生 JS 只控制工項選擇顯示及提交；所有授權、完整性、資格與 CAS 均在伺服器驗證。

## 仍未開通

廠商自助建立帳號未實作；既有登入/session 與各廠商讀取入口尚未全面接入 VR2，不能宣稱舊 runtime 已受此設定限制。本片不改 password、is_active、organization_status、既有 membership 狀態／role、registry、VR1 名冊／工項或內部 users／permissions。

未 push／merge／deploy，未 live 驗證。完成上限為 `VR3_PENDING_SCOPE_ADMIN_IMPLEMENTED_AND_TESTED / PENDING_EXTERNAL_REVIEW`。外審與 Second Copy 由後續 ChatGPT 流程處理；CLI exit 0 不等於產品 PASS，也不代表 CloudVerified／MAINLINE_READY。
