# 004F-VR4-PREVIEW-NAV/r02 隔離預覽導航修正

本輪最多 `PREVIEW_NAV_FIX_READY_PENDING_EXTERNAL_REVIEW`。
DEPLOYMENT=NOT_STARTED；BROWSER_REVIEW=PENDING；EXTERNAL_REVIEW=PENDING；SECOND_COPY=PENDING。
線上 404 的新授權候選；產品與發布舊輪封閉，r01 停止現場不重開。
本機 HTTP、合成模板／DOM、CLI exit 0 與 ZIP 均不代表產品 PASS 或雲端瀏覽器驗收。

## 基線與隔離

- 起點 `048f27807f89428301ad975aef420aa7721ac242`，tree `9c11aa43c9ec2a975a5ed44637ffcadca710691a`，231 tracked。
- 祖先產品版本 `a0eb5d2055ce047ce2eb5c862b6457853daa6643`，227 產品檔。
- 新工作根 `C:\Users\Public\Documents\004f-VR4-PREVIEW-NAV-20260928-r02`。
- Record `I:\公司web\record\product-mainline\vendor-id\004f\vr4-preview-nav-20260928-r02`。
- 七個既有允許檔為 base/sheet/vendor_scope_admin 模板、static/app.js、本 package 的 entry/fixture/README；新增 nav_smoke.py。
  產品只改四個呈現檔，其餘223產品檔、全tracked中scope外224檔保持raw bytes。不是227產品檔全不變。
- package路徑保留相容既有Gunicorn命令。fixture只改IDENTITY、BASELINE、WINDOWS_ROOT、RENDER_ROOT。
  preimport、SQLite guard、拒絕source.xlsx/alias/hardlink、exclusive startup、未知/partial DB拒絕、
  真schema/hash、default admin禁用、no fallback secret與固定只讀fixture-state契約均保留。
- 原smoke.py不改、不匯入、不執行；不重跑H9、舊RUN或完整suite。
- 只有entry在隔離驗證成功後注入server-side vr4_preview=True。query/cookie/form/localStorage不決定權限。
  沒有旗標或False維持正常產品呈現與JS；UI不是授權檢查，後端白名單始終有效。

## 點選步驟

1. 共用頁面顯示「VR4 隔離預覽・僅供測試」。匿名時提供「廠商申請」、「廠商登入」及「內部登入」。
   原申請頁拒絕已登入身分；內部登入後會明示並提供「登出以使用廠商申請／廠商登入」。
   按此按鈕沿原登出流程回登入頁，再由共用入口進入申請或廠商登入，不繞過原身分限制。
2. 內部管理員帳號 `vr4.preview.admin`，密碼來源為既有 **Render Environment**，本輪不讀取或輸出。
   本機smoke使用運行時生成、僅在記憶體及子程序環境中的臨時強密碼與APP_SECRET_KEY。
3. 依原登入流程選工地；頁首「廠商帳號與範圍管理」開啟 `/admin/vendor-scopes`，仍由原auth/admin role把關。
   保留真廠商選項及原表單，「返回管制表」回到 `/sheet`。此功能**不是「成員管理」**。
4. 管制表tabs切換當前工地既有表格，標題显示選中表名。展開、收納、選取工項/廠商、顯示選取項、列印可用。
   切換工地、內部登入/登出沿原流程。
5. `/vendor/register`可選公司並使用原申請流程；`/vendor/login`保留繁中頁面。
   本輪只驗新連結可達性，未重做申請提交、inactive登入或POST400回填。

本次預覽未開放：成員管理、表格設定、回復預設、進度/日期/額外欄位編輯、樓層/單戶報表、
工班/工作總覽API、需求確認、工班核准/取消。控制項disabled或改無href/action說明，
工班與工作總覽有明確fallback，浮動錨點仍有真目標。AI維持原「功能規劃中」。
預覽不啟動背景API或輪詢；顯示「唯讀預覽・重新整理更新」，重新整理取得最新資料。
沒有全域fetch偽造、假同步或假展示頁。

後端只增開原產品精確 `/sheet/<int:sheet_id>`、endpoint `sheet` 的GET/HEAD；保留 `/sheet`。
不泛允許sheet prefix、admin或api，不新增寫入method。匿名沿原登入；不存在及跨工地表格沿原導回契約。
route、login_required、resolve_sheet_id與load_grid不改。

## 最小驗證

在新repo執行 `C:\Python314\python.exe -B -m preview.vr4_20260928_r01.nav_smoke --evidence <本輪新證據目錄>`。
使用標準庫loopback真HTTP、CookieJar與正常登入，不mock current_user/session/response。
只驗新root/身份相關preimport拒絕、導航/tabs/工地/白名單/固定summary與DB原bytes不變。
fixture保留於新scratch，不進Record/ZIP；僅停止持有handle的本輪listener，記真PID/退出碼/port釋放。
安全事件不含密碼/hash/cookie/session/CSRF/snapshot、完整HTTP body/header、環境或DB內容。
既有Node `C:\Program Files\nodejs\node.exe` v24.18.0做--check與有界合成DOM/fetch行為檢查，
正常JS對照基線，preview無背景請求/寫入且保留純前端控制；這不是真瀏覽器。
模板使用合成render上下文對照基線無旗標/False，並非mock登入HTTP證據。
編譯不產repo pycache；tracked diff及新增smoke各自做whitespace檢查。
精確argv/cwd/exit、版本pins、失敗修正與結果以Record為準。

## 目前Render（使用者提供，本輪未查詢）

| 項目 | 值 |
| --- | --- |
| workspace | tea-d8vmr4ok1i2s73etn1tg |
| service | srv-dasvh9npn0mc73a97mrg |
| URL | https://handover-vr4-preview-20260928-r01.onrender.com |
| 現行branch | preview/004f-vr4-ux-20260928-r01 |
| 現行live commit | 048f27807f89428301ad975aef420aa7721ac242 |
| autoDeploy | no |
| 未來新branch | preview/004f-vr4-nav-20260928-r02 |

目前是已外審並成功SecondCopy的preview publish原件，不是舊9627032，也還不是本次導航修正。
本輪無新commit/push/部署，不存在可宣稱的新deployed SHA。

## 後續另行授權（只記錄，不執行）

1. 本輪原件外審接受 → 成功SecondCopy。
2. 受控本機commit/push新分支preview/004f-vr4-nav-20260928-r02，舊refs不回寫。
3. 既有Render切新branch並更新VR4_PREVIEW_MODE=004F-VR4-PREVIEW-NAV/r02、
   VR4_PREVIEW_ROOT=/tmp/004f-vr4-preview-nav-20260928-r02、
   APP_DB_PATH=/tmp/004f-vr4-preview-nav-20260928-r02/fixture.sqlite3；VR4_PREVIEW_RUNTIME=RENDER。
   secret/其他flags保留，不搬舊DB、不接真DB/磁碟、不另建服務。
4. Environment更新可能自動部署；先核對部署狀態，不能重複觸發。
5. 核對實際新deployed SHA及/preview/version的新identity/baseline/boot/fixture後，才做雲端瀏覽器驗收。
   /tmp冷啟動或重部署可能重建fixture，不能跨boot混證。
6. 原待完成申請、待開通提示、POST400回填遠端業務驗收仍PENDING，本輪本機smoke不能替代。

Gunicorn Start command保持package相容：

```sh
gunicorn preview.vr4_20260928_r01.entry:app --workers 1 --threads 1 --bind 0.0.0.0:$PORT --timeout 120 --access-logfile /dev/null --error-logfile - --log-level warning
```

來源前置引用外層inputs；來源後置PENDING_OUTER由外層合併核對。
不讀取/封裝_transport/cli、_handoff、rollout或歷史Record。
