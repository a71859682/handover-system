const syncState = document.getElementById("syncState");
const table = document.getElementById("controlTable");
const columnFilterStyle = document.getElementById("columnFilterStyle");
const crewFormShell = document.querySelector(".crew-form-shell");
const crewVendorList = document.getElementById("crewVendorList");
const crewBusinessDate = document.getElementById("crewBusinessDate");
const crewFormError = document.getElementById("crewFormError");
const progressControls = new Map();
const extraControls = new Map();
const parentCells = new Map();
const rowsByFloor = new Map();
const floorRows = [];
const unitRows = [];
const summaryCells = {
  done: new Map(),
  open: new Map(),
  total: new Map(),
  extraDone: new Map(),
  extraOpen: new Map(),
  extraTotal: new Map(),
};

let pendingSaves = 0;
const selectedTaskIds = new Set();
let activeDateInput = null;

function key(...parts) {
  return parts.join(":");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatCrewDate(value) {
  if (!value) return "";
  const match = String(value).trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return escapeHtml(value);
  return `${match[1]}年${match[2]}月${match[3]}日`;
}

function formatCrewDateTime(value) {
  if (!value) return "";
  const text = String(value).trim();
  const match = text.match(/^(\d{4}-\d{2}-\d{2})(?:[T\s](\d{2}:\d{2}))?/);
  if (!match) return escapeHtml(value);
  const formattedDate = formatCrewDate(match[1]);
  return match[2] ? `${formattedDate} ${match[2]}` : formattedDate;
}

function renderCrewFormError(error) {
  if (crewFormError) {
    crewFormError.textContent = error || "工班資料載入失敗";
    crewFormError.classList.remove("hidden");
  }
  if (crewVendorList) {
    crewVendorList.innerHTML = '<div class="crew-error-state">工班資料目前無法顯示，請稍後再試。</div>';
  }
}

function renderCrewForms(data) {
  if (!crewFormShell || !crewVendorList) return;
  if (crewFormError) {
    crewFormError.textContent = "";
    crewFormError.classList.add("hidden");
  }
  if (crewBusinessDate) {
    crewBusinessDate.textContent = formatCrewDate(data?.business_date || "");
  }

  const vendors = Array.isArray(data?.active_vendors) ? data.active_vendors : [];
  if (vendors.length === 0) {
    crewVendorList.innerHTML = '<div class="crew-empty-state">尚無今日工班資料</div>';
    return;
  }

  crewVendorList.innerHTML = vendors
    .map((vendor) => {
      const contact = vendor.contact || {};
      const entries = Array.isArray(vendor.work_entries) ? vendor.work_entries : [];
      const entryMarkup =
        entries.length > 0
          ? entries
              .map(
                (entry) => `
          <div class="crew-entry-row">
            <div><span class="crew-label">預計進場</span><strong>${escapeHtml(formatCrewDateTime(entry.planned_at || "")) || "—"}</strong></div>
            <div><span class="crew-label">預計進場人數</span><strong>${escapeHtml(entry.planned_headcount ?? 0)}</strong></div>
            <div><span class="crew-label">實際進場人數</span><strong>${escapeHtml(entry.actual_headcount ?? 0)}</strong></div>
            <div><span class="crew-label">施作內容</span><strong>${escapeHtml(entry.work_content || "—")}</strong></div>
            <div><span class="crew-label">各項目施作人數</span><strong>${escapeHtml(entry.work_headcount ?? 0)}</strong></div>
          </div>
        `,
              )
              .join("")
          : '<div class="crew-empty-state">尚無今日工班資料</div>';

      return `
        <article class="crew-vendor-card" data-vendor-name="${escapeHtml(vendor.vendor_name || "")}">
          <div class="crew-vendor-card-header">
            <h3>${escapeHtml(vendor.vendor_name || "未命名廠商")}</h3>
            <p>${escapeHtml(vendor.pending_items?.join("、") || "目前無待完成工項")}</p>
          </div>
          <div class="crew-vendor-meta">
            <div><span class="crew-label">聯絡人姓名</span><strong>${escapeHtml(contact.contact_name || "—")}</strong></div>
            <div><span class="crew-label">聯絡電話</span><strong>${escapeHtml(contact.contact_phone || "—")}</strong></div>
          </div>
          <div class="crew-entry-list">${entryMarkup}</div>
        </article>
      `;
    })
    .join("");
}

async function loadCrewForms(sheetId) {
  if (!crewFormShell || !sheetId) return;
  try {
    const response = await fetch(`/api/crew-forms?sheet_id=${encodeURIComponent(sheetId)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) {
      throw new Error(data?.error?.message || "crew forms request failed");
    }
    renderCrewForms(data);
  } catch (error) {
    renderCrewFormError(error?.message || "crew forms request failed");
  }
}

function setSyncState(text, className = "") {
  if (!syncState) return;
  syncState.textContent = text;
  syncState.className = `sync-state ${className}`.trim();
}

function buildDomCache() {
  document.querySelectorAll(".progress-select").forEach((el) => {
    progressControls.set(key(el.dataset.unitId, el.dataset.taskId), el);
  });
  document.querySelectorAll(".extra-input, .extra-select").forEach((el) => {
    extraControls.set(key(el.dataset.unitId, el.dataset.field), el);
  });
  document.querySelectorAll(".floor-row").forEach((row) => {
    const floorId = row.dataset.floorId;
    floorRows.push(row);
    rowsByFloor.set(floorId, []);
    row.querySelectorAll("[data-parent-task]").forEach((cell) => {
      parentCells.set(key(floorId, cell.dataset.parentTask), cell);
    });
    const handover = row.querySelector("[data-parent-handover]");
    if (handover) parentCells.set(key(floorId, "handover"), handover);
  });
  document.querySelectorAll(".unit-row").forEach((row) => {
    unitRows.push(row);
    rowsByFloor.get(row.dataset.floorId)?.push(row);
  });
  document.querySelectorAll("[data-summary-done]").forEach((el) => summaryCells.done.set(el.dataset.summaryDone, el));
  document.querySelectorAll("[data-summary-open]").forEach((el) => summaryCells.open.set(el.dataset.summaryOpen, el));
  document.querySelectorAll("[data-summary-total]").forEach((el) => summaryCells.total.set(el.dataset.summaryTotal, el));
  document.querySelectorAll("[data-extra-summary-done]").forEach((el) => summaryCells.extraDone.set(el.dataset.extraSummaryDone, el));
  document.querySelectorAll("[data-extra-summary-open]").forEach((el) => summaryCells.extraOpen.set(el.dataset.extraSummaryOpen, el));
  document.querySelectorAll("[data-extra-summary-total]").forEach((el) => summaryCells.extraTotal.set(el.dataset.extraSummaryTotal, el));
}

function toggleFloor(floorId, forceOpen = null) {
  const rows = rowsByFloor.get(String(floorId)) || [];
  const button = document.querySelector(`.toggle[data-floor-id="${floorId}"]`);
  const shouldOpen = forceOpen === null ? rows.every((row) => row.classList.contains("hidden")) : forceOpen;
  rows.forEach((row) => {
    row.classList.toggle("hidden", !shouldOpen);
    row.classList.remove("filtered-out");
  });
  const floorRow = document.querySelector(`.floor-row[data-floor-id="${floorId}"]`);
  floorRow?.classList.remove("filtered-out");
  if (button) button.textContent = shouldOpen ? "-" : "+";
}

function clearHighlights() {
  document.querySelectorAll(".selected-axis").forEach((el) => el.classList.remove("selected-axis"));
}

function highlightForControl(control) {
  clearHighlights();
  const unitRow = control.closest(".unit-row");
  if (!unitRow) return;
  const floorId = unitRow.dataset.floorId;
  const floorRow = document.querySelector(`.floor-row[data-floor-id="${floorId}"]`);
  floorRow?.querySelector("[data-floor-label]")?.classList.add("selected-axis");
  document.querySelector("[data-head-floor]")?.classList.add("selected-axis");
  document.querySelector("[data-head-unit]")?.classList.add("selected-axis");
  unitRow.querySelector("[data-unit-name]")?.classList.add("selected-axis");

  if (control.dataset.taskId) {
    document.querySelector(`[data-task-id="${control.dataset.taskId}"]`)?.classList.add("selected-axis");
    document.querySelector(`[data-vendor-task="${control.dataset.taskId}"]`)?.classList.add("selected-axis");
  }
  if (control.dataset.field) {
    document.querySelector(`[data-extra-head="${control.dataset.field}"]`)?.classList.add("selected-axis");
  }
}

function markTaskSelected(taskId) {
  const id = String(taskId);
  document.querySelector(`[data-task-id="${id}"]`)?.classList.add("selected-task");
  document.querySelector(`[data-vendor-task="${id}"]`)?.classList.add("selected-task");
}

function toggleTaskSelection(taskId) {
  const id = String(taskId);
  if (selectedTaskIds.has(id)) {
    selectedTaskIds.delete(id);
    document.querySelector(`[data-task-id="${id}"]`)?.classList.remove("selected-task");
    document.querySelector(`[data-vendor-task="${id}"]`)?.classList.remove("selected-task");
    return;
  }
  selectedTaskIds.add(id);
  markTaskSelected(id);
}

function clearTaskSelection() {
  selectedTaskIds.clear();
  document.querySelectorAll(".selected-task").forEach((el) => el.classList.remove("selected-task"));
}

function setStatusCell(cell, status) {
  if (!cell) return;
  cell.textContent = status;
  cell.classList.toggle("ok", status === "O");
  cell.classList.toggle("bad", status !== "O");
}

function setColumnFilter(taskIds = [], hideAll = false) {
  const ids = new Set([...taskIds].map((id) => String(id)).filter(Boolean));
  document.querySelectorAll(".task-col").forEach((cell) => {
    const taskClass = [...cell.classList].find((className) => className.startsWith("task-col-") && className !== "task-col");
    const taskId = taskClass ? taskClass.replace("task-col-", "") : "";
    cell.classList.toggle("hidden-task-col", hideAll || (ids.size > 0 && !ids.has(taskId)));
  });
  if (ids.size === 0 && !hideAll) {
    table?.classList.remove("filtered-columns");
    return;
  }
  table?.classList.add("filtered-columns");
}

function expandAll() {
  clearTaskSelection();
  setColumnFilter();
  floorRows.forEach((row) => row.classList.remove("filtered-out"));
  unitRows.forEach((row) => row.classList.remove("hidden", "filtered-out"));
  document.querySelectorAll(".toggle").forEach((button) => (button.textContent = "-"));
}

function collapseAll() {
  clearTaskSelection();
  setColumnFilter();
  floorRows.forEach((row) => row.classList.remove("filtered-out"));
  unitRows.forEach((row) => {
    row.classList.add("hidden");
    row.classList.remove("filtered-out");
  });
  document.querySelectorAll(".toggle").forEach((button) => (button.textContent = "+"));
}

function showSelectedTaskX() {
  if (selectedTaskIds.size === 0) {
    setColumnFilter([], true);
    return;
  }
  setColumnFilter(selectedTaskIds);
  floorRows.forEach((floorRow) => {
    const floorId = floorRow.dataset.floorId;
    let hasX = false;
    const rows = rowsByFloor.get(floorId) || [];
    rows.forEach((unitRow) => {
      const isX = [...selectedTaskIds].some((taskId) => progressControls.get(key(unitRow.dataset.unitId, taskId))?.value === "X");
      unitRow.classList.toggle("hidden", !isX);
      unitRow.classList.toggle("filtered-out", !isX);
      if (isX) hasX = true;
    });
    floorRow.classList.toggle("filtered-out", !hasX);
    const button = floorRow.querySelector(".toggle");
    if (button) button.textContent = hasX ? "-" : "+";
  });
}

async function resetSheetDefaults() {
  const button = document.getElementById("resetSheetBtn");
  if (!button) return;
  const password = window.prompt("請輸入管理員密碼，確認後會將目前管制表全部回復為預設值。");
  if (password === null) return;
  if (!window.confirm("確定要將所有下拉選單改回 X，並清空所有日期嗎？")) return;

  pendingSaves += 1;
  setSyncState("回復中", "saving");
  try {
    const response = await fetch("/api/reset-sheet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password, sheet_id: button.dataset.sheetId || table?.dataset.sheetId }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || "回復失敗");
    clearTaskSelection();
    setColumnFilter();
    applyGrid(data.grid);
    setSyncState("已回復預設");
  } catch (error) {
    window.alert(error.message || "回復失敗，請確認管理員密碼。");
    setSyncState("回復失敗", "error");
  } finally {
    pendingSaves -= 1;
    clearHighlights();
  }
}

async function postJson(url, payload) {
  pendingSaves += 1;
  setSyncState("儲存中", "saving");
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("save failed");
    const data = await response.json();
    applyGrid(data.grid);
    setSyncState("已同步");
  } catch {
    setSyncState("儲存失敗", "error");
  } finally {
    pendingSaves -= 1;
    clearHighlights();
  }
}

function saveProgress(select) {
  return postJson("/api/progress", {
    unit_id: select.dataset.unitId,
    task_id: select.dataset.taskId,
    value: select.value,
  });
}

function saveExtra(control) {
  return postJson("/api/unit-extra", {
    unit_id: control.dataset.unitId,
    field: control.dataset.field,
    value: control.value,
  });
}

function applyGrid(grid) {
  for (const [progressKey, value] of Object.entries(grid.progress)) {
    const control = progressControls.get(progressKey);
    if (control && document.activeElement !== control && control.value !== value) control.value = value;
  }
  for (const [unitId, extra] of Object.entries(grid.extras)) {
    for (const field of grid.extra_fields || []) {
      const fieldKey = field.field_key;
      const control = extraControls.get(key(unitId, fieldKey));
      const nextValue = extra[fieldKey] || (field.field_type === "status" ? "X" : "");
      if (control && document.activeElement !== control && control.value !== nextValue) control.value = nextValue;
    }
  }
  for (const floorItem of grid.floors) {
    const floorId = String(floorItem.floor.id);
    for (const [taskId, status] of Object.entries(floorItem.parent_status)) {
      setStatusCell(parentCells.get(key(floorId, taskId)), status);
    }
  }
  for (const [taskId, values] of Object.entries(grid.summary)) {
    const done = values.done;
    const total = values.total;
    const open = total - done;
    if (summaryCells.done.get(taskId)) summaryCells.done.get(taskId).textContent = done;
    if (summaryCells.open.get(taskId)) summaryCells.open.get(taskId).textContent = open;
    if (summaryCells.total.get(taskId)) summaryCells.total.get(taskId).textContent = total;
  }
  for (const [field, values] of Object.entries(grid.extra_summary || {})) {
    const done = values.done;
    const total = values.total;
    const open = total - done;
    if (summaryCells.extraDone.get(field)) summaryCells.extraDone.get(field).textContent = done;
    if (summaryCells.extraOpen.get(field)) summaryCells.extraOpen.get(field).textContent = open;
    if (summaryCells.extraTotal.get(field)) summaryCells.extraTotal.get(field).textContent = total;
  }
}

async function refreshGrid() {
  if (pendingSaves > 0 || document.activeElement?.matches("select,input")) return;
  try {
    const response = await fetch("/api/grid");
    if (!response.ok) return;
    applyGrid(await response.json());
    setSyncState("已同步");
  } catch {
    setSyncState("同步失敗", "error");
  }
}

function showDatePopover(input) {
  activeDateInput = input;
  const popover = document.getElementById("datePopover");
  if (!popover) return;
  const rect = input.getBoundingClientRect();
  popover.style.left = `${rect.left + window.scrollX}px`;
  popover.style.top = `${rect.bottom + window.scrollY + 4}px`;
  popover.classList.remove("hidden");
}

function hideDatePopover() {
  document.getElementById("datePopover")?.classList.add("hidden");
}

function updatePrintDate() {
  const target = document.getElementById("printDate");
  if (!target) return;
  const now = new Date();
  target.textContent = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`;
}

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".toggle");
  if (toggle) return toggleFloor(toggle.dataset.floorId);

  const head = event.target.closest(".selectable-head[data-task-id], .selectable-head[data-vendor-task]");
  if (head) {
    toggleTaskSelection(head.dataset.taskId || head.dataset.vendorTask);
    return;
  }

  if (event.target.closest("#expandAllBtn")) return expandAll();
  if (event.target.closest("#collapseAllBtn")) return collapseAll();
  if (event.target.closest("#showSelectedBtn")) return showSelectedTaskX();
  if (event.target.closest("#resetSheetBtn")) return resetSheetDefaults();
  if (event.target.closest("#printBtn")) {
    updatePrintDate();
    return window.print();
  }
  if (event.target.closest("#dateClearBtn")) {
    if (activeDateInput) activeDateInput.value = "";
    return;
  }
  if (event.target.closest("#dateConfirmBtn")) {
    if (activeDateInput) saveExtra(activeDateInput);
    return hideDatePopover();
  }
});

document.addEventListener("focusin", (event) => {
  const control = event.target.closest(".progress-select, .extra-input, .extra-select");
  if (!control) return;
  highlightForControl(control);
  if (control.classList.contains("extra-input")) showDatePopover(control);
});

document.addEventListener("focusout", (event) => {
  if (!event.target.closest(".progress-select, .extra-input, .extra-select")) return;
  window.setTimeout(() => {
    if (!document.activeElement?.matches(".progress-select, .extra-input, .extra-select")) {
      clearHighlights();
      hideDatePopover();
    }
  }, 0);
});

document.addEventListener("change", (event) => {
  const progress = event.target.closest(".progress-select");
  if (progress) return saveProgress(progress);
  const extra = event.target.closest(".extra-select");
  if (extra) return saveExtra(extra);
});

buildDomCache();
updatePrintDate();
if (crewFormShell?.dataset.sheetId) {
  loadCrewForms(crewFormShell.dataset.sheetId);
}
setInterval(refreshGrid, 10000);
