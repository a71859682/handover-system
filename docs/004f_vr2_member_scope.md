# 004F-VR2/r02：成員工地與工項 scope service

本片新增可持久化的成員配置、可信內部管理預覽及共用有效 task resolver。
完成層級最多為 `VR2_SCOPE_SERVICE_IMPLEMENTED_AND_TESTED / PENDING_EXTERNAL_REVIEW`。
未建立 public route、UI、帳號開通、runtime 接線、部署或正式資料轉換。

## 基線與範圍

- 分支：`feature/004f-vr2-member-scope`。
- HEAD：`7506c91df010bdb4a2e1188ebb889ed19289fc5d`。
- tree：`c4298667c48c4a8adc2ae3f3b1fa370f95e2dd9c`。
- parent：`ef0554d02343addf3156985aa217fc64f07e50f9`。
- 只新增本文件、`services/vendor_access_service.py`、`tests/test_vendor_access_service.py`。
- 不改 VR1 四檔、app、四表 guard、路由、UI、帳號狀態、registry 或正式 DB。
- service 不 import app、不建立連線、不尋找 DB、不 bootstrap、不連外。
- H9、Render、SSH、PostgreSQL、新安裝、新連接、Git mutation、push/merge/deploy 均不使用。

## 呼叫契約

以下是未接線的內部 Python API；不是可直接開放的 HTTP payload。
控制器先從已驗證的 internal 登入身分取得 user ID，再建構
`InternalActor(user_id)`。此型別表達身分來源，不是密碼或防偽 token；
禁止由 request body、vendor session 或任意數字轉成 internal actor。
service 每次另查 `main.users.role`，依現有 global-admin 規則
`str(role or '').strip() == 'admin'` 判定，不信 caller 提供的 role/is_admin。
users 沒有 is_active 欄位，不杜撰檢查；site admin 與 vendor owner 不具管理權。
相同數字的 internal user 與 vendor account 仍是不同身分類型。

| API | 行為與必要條件 |
| --- | --- |
| `initialize_schema(conn)` | 明確初始化四張 VR2 補充表；FK 必須先啟用，caller 已 BEGIN；呼叫前既有 core exact guard 應已通過 |
| `save_scopes(conn, *, actor, membership_id, scopes, expected_revision, reason)` | 可信 internal global admin 保存某 membership 的完整工地配置；回傳 revision；caller 持有交易 |
| `preview_scopes(conn, *, actor, membership_id)` | 管理預覽配置、當期合格 task 與有效範圍；可在管理交易內呼叫，不得將結果當跨請求授權快取 |
| `resolve_scope(conn, *, vendor_account_id)` | 可信 vendor 登入邊界取得 account ID；連線不得已有交易；一次呼叫使用一個新一致快照；無 admin bypass |

保存示意（ID 均須來自目標隔離／受控 DB 的真實記錄）：

```python
from services.vendor_access_service import InternalActor, save_scopes

# conn 的 FK 在 BEGIN 前啟用；既有 schema 與 VR1/VR2 補充 schema 已就緒。
conn.execute("BEGIN")
revision = save_scopes(
    conn,
    actor=InternalActor(authenticated_internal_user_id),
    membership_id=current_membership_id,
    scopes=[{
        "site_id": site_id,
        "assignment_id": assignment_id_seen_by_editor,
        "mode": "SELECTED",
        "task_ids": [stable_task_id],
    }],
    expected_revision=revision_seen_by_editor,
    reason="管理者調整成員工項範圍",
)
# commit/rollback 由 caller 決定；service 不結束 caller 的交易。
```

首次配置 expected_revision 為 0；後續用管理預覽取得的 revision。
每站四個欄位皆必填，mode 缺省不轉成 ALL。ALL 的 task_ids 必須為空；
SELECTED 空清單代表零工項。ID 要求正整數，不接受 bool 或字串代替數字。
membership ID 為小寫 canonical UUID v4。

assignment_id 必須是管理畫面／受控流程實際讀到的當期世代。
service 查核它等於目標 vendor/site 唯一 active assignment，且 site active。
缺關係回報「尚未建立廠商工地關係」，不自動建 link。
若 assignment 已換 successor，舊畫面保存會得到 `ScopeConflict`，不能只靠舊
revision 悄悄綁到新 assignment；重新讀取並明確提交新 ID 才能重授權。
初始化前的控制器可從既有關係管理流程取得 assignment ID；本片沒有新增
公開的關係查詢或建立入口。

## 儲存、世代、撤權及並行

四個補充表使用 `vr2_` 命名空間，不占用 exact guard 保留前綴：

| 表 | 保存內容 |
| --- | --- |
| `vr2_scope_versions` | membership PK、首次保存的 vendor/account 身分、revision、最後管理者／時間／理由 |
| `vr2_site_scopes` | membership/site PK、該次 assignment ID、ALL/SELECTED |
| `vr2_selected_tasks` | membership/site/task PK；隨 scope 刪除 cascade 清除 |
| `vr2_scope_events` | membership/revision PK、管理者、時間、理由及完整配置 JSON；service 只新增變更事件 |

配置 anchor 綁住 membership 當時的 vendor/account；原地改隸後保存、預覽或有效
讀取均拒絕該身份，必須走新 membership ID。revoked membership 不可保存；
pending/active 可保存，profile 必須存在、organization 必須 active 或 disabled。
account inactive、organization disabled 或 pending membership 的配置不產生有效授權。

保存驗證整批輸入後才寫入，遺漏工地即撤除。`scopes=[]` 撤除全部但保留版本
及事件，避免舊畫面用 revision 0 復活。切換 mode 會替換 selected 清單，無殘留。
同內容且同 revision 的重存回傳原 revision、不寫入、不增加重複列；不同內容
或新 assignment 世代才增加 revision。過期 revision 即使內容相同仍拒絕。
記錄的是配置變更；相同內容的重送不是另一筆變更事件。

SQLite 的 caller 交易與巢狀 savepoint 保護 DDL、版本 CAS、整批替換及事件新增。
版本不符為 `ScopeConflict`。若 caller 在 WAL 舊快照上升級為 writer，SQLite
可能回報 `OperationalError`/BUSY_SNAPSHOT；service 回復自己的 savepoint 並保留
caller 交易，控制器須結束該舊管理交易、重新讀取後由管理者決定，不可盲目重送。
service 不執行 executescript、commit 或 connection.rollback。

撤除只影響目標 membership 配置，不改 account、membership、organization、
工項歸屬、工地關係或其他成員。membership 重入使用 successor ID；assignment
撤銷重建使用 successor ID。兩種世代都不繼承舊 scope。
本 service 不追蹤外部將同一 ID 的 status 關閉再打開的歷史；身份／關係生命週期
控制器必須遵守 successor 契約，不得以原地重用身份取代新世代。

## 有效讀取與輸出

resolver 只接收可信的 vendor_account_id，DB 推導唯一 active membership 與 vendor。
每次確認 account.is_active=1、organization active、VR1 profile 存在，並比對配置
anchor。新呼叫不能使用既有長交易／session scope 保留舊授權；有既存交易時
回傳零範圍 `scope_unavailable`，保留 caller 的原交易與資料不變。
管理 preview 可用管理交易，但不是有效請求授權的替代入口。

每個回傳 task 都需同時滿足：active site、明確已配置該 site、配置引用的當期
assignment active 且 vendor/site 完全相符、active binding 的 vendor/site/assignment
全部一致、sheet 實際位於該 site、task 實際位於該 sheet、VR1 task assignment
vendor 等於該 membership vendor。ALL 動態包含合格 tasks；SELECTED 再與已保存
task IDs 取交集。保存 SELECTED 時每個 ID 都必須合格，不能靜默丟棄非法 ID。
綁定關係歧義或不一致不授權；同名工項完全按 task ID 分開。

管理保存、preview 及 resolver 共用 `_eligible` 的完整交集判定。同工地新表格
須先由受控流程建立合格 binding，ALL 才會納入；新工地永不自動選取。
task 改隸、sheet 移站、關係失效均於新快照重新判斷。

有效輸出為 `{sites, task_count, reason}`；sites 包 site_id/site_name/sheets/task_count，
sheets 包 sheet_id/sheet_name/tasks/task_count，tasks 只有 task_id/task_name。
先過濾才分組計數；無有效 task 的工地／表格不出現在有效結果，避免名稱或數量洩漏。
`reason` 是空集合／未生效的一般代碼，不回傳 DB 錯誤或其他成員資料。
schema 缺失、不相容、主表不是 table、FK 未開、TEMP 同名物件或新表 trigger
均 fail closed；resolver 不建表、不修復、不生成 link、不退回名稱授權。
未知 mode 與 ALL 殘留 selected 資料亦拒絕。

管理預覽另含 revision、configured_scopes（保存的 IDs）、configured_scope
（配置與當期有效關係交集）、effective_scope、inactive_reason、site_issues。
配置可能仍留著已失效 IDs，僅供管理者辨識；它們不進入有效集合。
空集合的 site_issues 用 `no_current_eligible_tasks`，不嘗試猜測是哪一個外部流程
撤銷關係。inactive_reason 區分 account、membership、organization 等未生效條件。

## 隔離與行為驗證

測試只在全新 TemporaryDirectory 下的 DB 建造／複製 fixture。重用已接受 VR1
fixture/service，不重跑其 16 個 unittest。parent 不 import app；guard 子程序
在首次 app import 前限定 fresh APP_DB_PATH、清空 DATABASE_URL／DUAL_WRITE_TABLES、
關閉六個 backend flags，audit hook 禁止其他 SQLite 路徑及網路，再進行 bootstrap。
fixture 內啟用帳號或更改關係只是合成測試資料，不是正式帳號操作。

| 驗收面向 | 測試行為 |
| --- | --- |
| 持久化／冪等 | commit、關閉重開、同內容不同輸入順序不增列、事件保存、原表完整快照保留 |
| 管理身分 | 真正 internal admin；普通 internal、site admin、vendor owner 原數字、混淆／偽造 actor、不存在 ID 皆無寫入；即時查 role |
| ALL／SELECTED | 兩工地多表、同名 IDs、動態 task／受控 binding、新工地不自動加入、SELECTED 空集合及 mode 切換 |
| 輸入拒絕 | 非法 ID、跨 vendor/site、未指派／未綁定 task、缺 mode、ALL 帶清單、重複及任意 vendor 欄；全表與 total_changes 不變 |
| 世代 | revoked／successor membership、原地 vendor/account 改隸、assignment successor 舊配置無效且舊畫面不能重授權 |
| 撤权／隔離 | 第二連線依次撤 account、membership、org、site、assignment、binding；其他成員獨立 |
| 一致性 | FK 全有效但關係跨表不一致仍拒絕；task 改隸、sheet 移站；損壞 mode／active membership 歧義 fail closed |
| 配置與生效 | pending/inactive/disabled 保存與預覽可用，有效集合為零；沒有 bypass 參數 |
| 並行 | 新版本撤權擋住舊 editor；WAL 舊 writer 快照不能覆蓋撤權；請求中並行撤權保有單一快照，下次請求即為空 |
| 交易 | 成功不 commit caller；寫入／DDL 中途故障只回復本次操作，保留 caller 其他工作 |
| 相容性 | 真實 app exact guard 初始化前、DDL 後、保存後均 all_exact；FK 實際約束、main/TEMP table/view/trigger、唯讀 authorizer |

指定驗證命令：

```text
python -m unittest discover -s tests -p test_vendor_access_service.py -v
python -m py_compile services/vendor_access_service.py tests/test_vendor_access_service.py
git diff --check
```

untracked 三檔另做 byte identity、可還原 new-file patch 與 patch whitespace 核對，
不能以空的 tracked git diff 宣稱已審查新檔。命令、真實 exit、必要失敗診斷、
最終基線、status、交付副本、patch、回讀 manifest 直接保存本輪 Record：
`I:\公司web\record\product-mainline\vendor-id\004f\vr2-20260927-r02\evidence`。
ZIP 在 `_transport`，產品指標在 `_handoff`；不包含 DB、密鑰、.git、repo 或舊包。

外層保存的 active NATIVE/STDERR 與 CLI 產生的 FINAL 不由產品封装讀取或預報 hash。
CLI 真退出後由外層 `CLI-CLOSE.txt` 收尾。Mirror 外審、CloudVerified、Second Copy
與 MAINLINE_READY 不由本片預告；以實際回讀與後續獨立收據為準。

## 後續仍需完成

帳號 pending 建立、管理畫面及受控關係維護、正式開通與所有讀取入口／清單／
計數／明細／列印／API／舊 session 失效都尚未接線。可看 task 不增加填報、
編輯、刪除或核准權限。service 沒有提供混合 vendor_work_entries 內容授權；
SELECTED 在內容缺乏明確 task 關聯時必須拒絕整筆，ALL 也不能只靠旧 vendor_name。
不得因 sheet 裡有一個可見 task 就放行整筆混合內容。
正式替換／啟用另需綁定目標環境、DB、一致可回復備份及完整 runtime 整合。
