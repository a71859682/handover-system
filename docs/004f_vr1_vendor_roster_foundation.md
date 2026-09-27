# 004F-VR1/r01 廠商名冊與工項歸屬 service

基線為 `a71859682/handover-system` 的
`ef0554d02343addf3156985aa217fc64f07e50f9`；工作分支
`feature/004f-vr1-roster-foundation`。本片提供可持久化的管理層內部
SQLite service，尚未接入 runtime、路由、UI 或帳號授權。

本片僅新增以下四檔：

| 檔案 | 用途 |
| --- | --- |
| `services/vendor_roster_service.py` | 明確初始化、整批匯入、task ID 匹配及持久化讀取 |
| `tests/test_vendor_roster_service.py` | 新建隔離 fixture DB 的必要行為及實際既有 guard 測試 |
| `tests/fixtures/vendor_roster_20260927.json` | 16 家核對名冊、明示別名、來源列及修正軌跡 |
| `docs/004f_vr1_vendor_roster_foundation.md` | 資料、API、交易、測試及未完成邊界 |

## 呼叫方式與交易所有權

service 僅接收呼叫端傳入的 `sqlite3.Connection`，不找路徑、不開連線、
不 import app、不 bootstrap/seed、不讀環境設定。既有核心 schema 須已由
呼叫端的既有流程準備並通過原 guard。不得將此範例直接套用 live DB。

```python
from services.vendor_roster_service import (
    initialize_schema, apply_roster, list_profiles, list_task_assignments,
)

# conn 由管理流程提供；外鍵必須在 BEGIN 之前已啟用並確認。
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("BEGIN")
try:
    initialize_schema(conn)
    result = apply_roster(conn, verified_entries, task_ids=[301, 302])
    profiles = list_profiles(conn)
    tasks = list_task_assignments(conn, task_ids=[301, 302])
    conn.commit()  # 只有呼叫端能決定提交
except Exception:
    conn.rollback()  # 只有呼叫端能決定撤銷整個外層交易
    raise
```

寫入 API 要求已啟用外鍵且外層交易有效，否則拒絕。service 每次操作使用
獨立 savepoint；成功只 release 該 savepoint，不 commit；失敗只 rollback
本次 savepoint，不 rollback 呼叫端其他變更。DDL 也在 savepoint 內。
因此呼叫端即使成功匯入，未 commit 就關閉連線仍會失去未提交內容。
測試另證明由呼叫端 commit、關閉及重開後可讀且 ID 不變。

## 補充表與輸入

`vendor_profiles` 為 STRICT table；`vendor_id` 同時是主鍵及既有
`vendor_organizations.vendor_id` 外鍵。`tax_id` 為唯一八位 ASCII 數字文字，
另存 `legal_name`、`display_name`、`aliases_json`、`source_json`。
內部 ID 為新產生的 canonical UUID v4。新 organization 的 display_name
採名冊簡稱，狀態固定 `disabled`，並填入既有建立／更新稽核欄位。
不依名稱接管同名舊 organization。

`task_vendor_assignments` 為 STRICT table；`task_id` 是主鍵並參照既有
`tasks.id`，`vendor_id` 參照 profile，故一個 task 至多一筆當期歸屬。
另存 `matched_name`、`match_basis='explicit_name_exact_trim'` 及當時 profile
來源的 `source_json`。刪除仍被參照的 task／profile／organization 由 FK 拒絕。
無 assignment 表示待指定。沒有建立額外 runtime 權限表或冒名廠商。

兩表的完整 SQL 在 service 的 `_SCHEMA`；不修改既有四表的 SQL、索引或 guard，
不使用它們的保留命名前綴。初始化可重跑，既有補充表定義不相容時拒絕。
寫入目標表上的 main／TEMP triggers 亦拒絕，避免其副作用破壞保護資料或外層交易。
所有業務查詢及寫入明確使用 main schema，TEMP 同名表不能導向錯誤資料。

`apply_roster(conn, entries, *, task_ids=())` 接受 list；每列必須正好包含：

| 欄位 | 契約 |
| --- | --- |
| `tax_id` | 八位 ASCII 數字的 str；拒絕數字型別、全形數字、空白、重複值，不猜測補零 |
| `legal_name` | 非空、無 NUL、無邊界空白的正式名 |
| `display_name` | 同上，長度最多 100，作 organization 顯示名 |
| `aliases` | 明示別名的字串 list，可為空；不從來源原名／工地註記生成別名 |
| `source` | JSON object；至少 document、version、sheet、正整數 row、source_original_name；保留其他來源資訊 |

`source.source_original_name` 保留來源原始公司名。原件名稱、
10810 bytes、SHA256、Sheet1 列號及 r02 版本均保留在 JSON。浤淋同時保留
原數字 `252579`、使用者補充值 `00257979` 與有效文字 `00252579`，並記錄
交接提供的核對連結。這些來源資訊引用本包 ROSTER.md，沒有重新開啟原件、
封閉 r02 包或重新查詢外網。

大英的正式名為「大英營造有限公司」，原名「大英營造有限公司-新埔段」及
來源工地註記「新埔段」分別保留；後者不產生 site assignment。凱思登正式名、
凱斯登簡稱以及隆昌新竹分公司獨立身分均保留。名冊中的「—」轉為空 aliases。

## 匹配、重跑與拒絕

`task_ids` 必須為不重複正整數的 list／tuple；預設空集合只匯入名冊，
不隱式掃描並綁定所有 task。指定不存在的 task、非法來源或非法統編，整批拒絕。

候選集合包含 DB 全部既有 profiles 及本批新 profiles。只用正式名、簡稱及
明示別名，對 `tasks.vendor` 去除邊界空白後精確匹配，不做 NFKC、大小寫摺疊、
模糊比對、內部空白移除或拼字修復。同一廠商的重複名稱只算一個候選。

- 唯一候選且未綁定：新增 assignment，回傳 `matched`。
- 唯一候選且已綁定同廠商：無寫入，回傳 `already_assigned`。
- 未綁定而無候選／多候選：回傳 `unmatched`／`ambiguous`、`pending=True`，無 assignment。
- 已有歸屬卻匹配不同廠商、變成無候選或多候選：`RosterConflict`，整批無部分寫入，既有歸屬保持原狀。
- 同統編任何 profile 內容衝突、profile 與 organization 顯示名不一致、既有關係違反 FK：整批拒絕。

相同統編且相同完整內容沿用 vendor_id；JSON object key 順序不影響比較，
aliases 的 list 順序與來源值保留。既有 organization 合法狀態不會被本 service
更動。改名、合併、來源版本更新或重綁不是本次 API 的隱式行為。

回傳 dict 含 `vendor_ids`（統編到 ID）、`created_vendor_ids`、
`assignments_created`（task IDs）及逐 task 結果；逐項含 task_id、status、
vendor_id、candidate_vendor_ids、pending。`RosterError` 表示拒絕條件；
`RosterConflict` 為其子類。SQLite 操作錯誤回復自身 savepoint 後向外傳遞。

`list_profiles(conn)` 從 DB 重讀且核對 organization 對應；
`list_task_assignments(conn, task_ids=None)` 回傳全部或指定 task 的 ID、
sheet/site、原工項名稱、原 vendor 文字、歸屬、依據及 pending。查詢不授權。

## 必要測試與資料保留

```text
python -m unittest discover -s tests -p test_vendor_roster_service.py -v
python -m py_compile services/vendor_roster_service.py tests/test_vendor_roster_service.py
git diff --check
```

focused suite 有 16 個 tests，涵蓋本片必要完成條件；輸出與真實 exit code
保存在 result。沒有啟動全 repo 歷史資格鏈。

測試所有 DB 均新建於 `TemporaryDirectory`，每個 case 使用新副本；app
只在獨立測試子程序載入。父程序不改環境；子程序啟動時先設定 APP_DB_PATH，
清空 DATABASE_URL／DUAL_WRITE_TABLES，停用 USE_SQLALCHEMY_READS、
USE_SQLALCHEMY_WRITES、USERS_READ_COMPARE、DUAL_WRITE_ENABLED、
DUAL_WRITE_DRY_RUN、DUAL_WRITE_STRICT。載入 app 前核對路徑與環境；
子程序 audit hook 拒絕任何非指定 fixture 的 SQLite 連線及網路連線。
預先寫入 fixture 的 excel_seeded 標記，避免 bootstrap 載入 source.xlsx。
既有 app 的初始化僅在此新建 fixture 發生；未對 live DB 執行。

16 家內容及來源逐項核對，包含前導零與例外名稱。12 筆同名 task 分佈在
兩個測試工地、三張表；比對完整 tasks 列，含 ID、sheet_id、col_index、
vendor、location、name。全表 before/after snapshot 同時比較工地、表格、
floors、units、progress、extra、內部 users／權限、舊帳號、舊四表資料及
global registry；只允許增加新 organization 及兩張補充表資料。

DDL 第二表建立失敗、第二筆 profile 寫入失敗均有注入測試，證明回復自身
操作並保留呼叫端變更；修復注入後可重試。外層 rollback 能撤銷成功匯入及
DDL。外鍵有效時直接插入不存在 task／vendor 或重複 assignment 皆被 SQLite
拒絕。另有單獨 FK OFF 拒絕測試，未以停用 FK 通過任何匯入。

實際 `app.ensure_vendor_organization_schema` 在補充表前、補充表後、16 家
匯入後及相同輸入重跑後均應回傳 `all_exact`；未 mock 或擷取改寫 guard。

## 交付與後續邊界

本片不 commit/push/merge/deploy。result 交付四檔可還原 PATCH.diff、
四檔副本、測試輸出、基線／完整 status 及 SHA256 證據；封裝不含 DB、
密鑰、整個 repo 或舊包。取回驗證結果以 RESULT.md 的實測紀錄為準。

runtime/UI、舊帳號重置、live DB 資料替換、部署及正式備份均未完成。
未建立帳號、owner、membership、成員工地授權或 sheet binding；
沒有一般成員可呼叫的 public API。VR2/VR3 和正式替換仍需後續實作與外審。
本地測試／ZIP 不宣告 Record/Mirror/SecondCopy 閉合，CloudVerified=false。
原生 JSONL 由外層 CLI 保存；本片不讀 active rollout、不補寫原生終止事件。
