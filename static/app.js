const syncState = document.getElementById("syncState");
const table = document.getElementById("controlTable");
const columnFilterStyle = document.getElementById("columnFilterStyle");
const crewFormShell = document.querySelector(".crew-form-shell");
const crewVendorList = document.getElementById("crewVendorList");
const crewBusinessDate = document.getElementById("crewBusinessDate");
const crewFormError = document.getElementById("crewFormError");
const crewWorkHubCards = document.getElementById("crewWorkHubCards");
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

function buildCrewWorkHubCardMeta(summary = {}) {
  return [
    {
      action: "blocked",
      testId: "crew-work-hub-card-blocked",
      title: "Blocked",
      value: summary.blocked_count ?? 0,
      summaryKey: "blocked_count",
    },
    {
      action: "pending-approval",
      testId: "crew-work-hub-card-pending-approval",
      title: "待正式核准",
      value: summary.pending_approval_count ?? 0,
      summaryKey: "pending_approval_count",
    },
    {
      action: "pending-requirement",
      testId: "crew-work-hub-card-pending-requirement",
      title: "待確認需求",
      value: summary.pending_requirement_count ?? 0,
      summaryKey: "pending_requirement_count",
    },
    {
      action: "today-entries",
      testId: "crew-work-hub-card-today-entry",
      title: "今日進場",
      value: summary.today_entry_count ?? 0,
      summaryKey: "today_entry_count",
    },
  ];
}

function renderCrewWorkHubCards(data) {
  if (!crewWorkHubCards) return;
  const summary = data?.summary || {};
  const cards = buildCrewWorkHubCardMeta(summary);
  crewWorkHubCards.innerHTML = cards
    .map(
      (card) => `
        <article
          class="crew-work-hub-card"
          data-testid="${card.testId}"
          data-work-hub-action="${card.action}"
          style="border:1px solid #d9e2ec;border-radius:16px;padding:14px 16px;background:linear-gradient(180deg,#ffffff 0%,#f5f8fb 100%);box-shadow:0 8px 20px rgba(15,23,42,0.06);min-height:88px;display:flex;flex-direction:column;justify-content:space-between;"
        >
          <span class="crew-label">${escapeHtml(card.title)}</span>
          <strong data-testid="crew-work-hub-card-value-${card.summaryKey}" style="font-size:1.75rem;line-height:1.1;">${escapeHtml(card.value)}</strong>
        </article>
      `,
    )
    .join("");
  crewWorkHubCards.style.display = "grid";
  crewWorkHubCards.style.gridTemplateColumns = "repeat(auto-fit, minmax(140px, 1fr))";
  crewWorkHubCards.style.gap = "12px";
  crewWorkHubCards.style.margin = "0 0 16px";
}

function findCrewWorkHubTarget(action) {
  if (!crewVendorList) return null;
  if (action === "blocked") {
    return crewVendorList.querySelector("[data-work-hub-blocked='true']") || crewVendorList;
  }
  if (action === "pending-approval") {
    return crewVendorList.querySelector("[data-work-hub-pending-approval='true']") || crewVendorList;
  }
  if (action === "pending-requirement") {
    return crewVendorList.querySelector("[data-work-hub-pending-requirement='true']") || crewVendorList;
  }
  return crewVendorList;
}

function scrollCrewWorkHubToTarget(action) {
  const target = findCrewWorkHubTarget(action);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function buildCrewRequirementMeta(entry) {
  const requirementText = String(entry?.pre_entry_requirement || "").trim();
  const requirementStatus = String(entry?.requirement_status || "pending").trim() || "pending";
  const confirmedBy = String(entry?.requirement_confirmed_by || "").trim();
  const confirmedAt = String(entry?.requirement_confirmed_at || "").trim();
  const isConfirmed = requirementStatus === "confirmed";
  const requirementDisplay = requirementText || "未填寫";
  const confirmedMeta =
    isConfirmed && (confirmedBy || confirmedAt)
      ? `<div data-testid="crew-work-entry-requirement-confirmed-meta"><span class="crew-label">確認資訊</span><strong data-testid="crew-work-entry-requirement-confirmed-by">${escapeHtml(confirmedBy || "已確認")}</strong>${confirmedAt ? `<span data-testid="crew-work-entry-requirement-confirmed-at">${escapeHtml(formatCrewDateTime(confirmedAt))}</span>` : ""}</div>`
      : "";
  const actionMarkup = isConfirmed
    ? ""
    : `<button type="button" class="crew-confirm-btn" data-testid="crew-work-entry-requirement-confirm-action" data-entry-id="${escapeHtml(entry?.id ?? "")}" data-sheet-id="${escapeHtml(entry?.sheet_id ?? "")}">確認進場前需求</button>`;
  return {
    requirementDisplay,
    requirementStatus,
    confirmedMeta,
    actionMarkup,
  };
}

function buildCrewReadinessMeta(entry) {
  const readinessState = String(entry?.readiness_state || "").trim();
  const readinessReason = String(entry?.readiness_reason || "").trim();
  let readinessLabel = "進場條件狀態未定義";

  if (readinessState === "not_ready" && readinessReason === "requirement_pending") {
    readinessLabel = "尚未具備進場條件";
  } else if (readinessState === "ready" && readinessReason === "requirement_confirmed") {
    readinessLabel = "需求已確認";
  } else if (readinessState === "ready" && readinessReason === "no_requirement") {
    readinessLabel = "無進場前需求";
  }

  return {
    readinessState,
    readinessReason,
    readinessLabel,
  };
}

function buildCrewSchedulingGateMeta(entry) {
  const schedulingGateState = String(entry?.scheduling_gate_state || "").trim();
  const schedulingGateReason = String(entry?.scheduling_gate_reason || "").trim();
  let schedulingGateLabel = "";

  if (schedulingGateState === "warning" && schedulingGateReason === "requirement_pending") {
    schedulingGateLabel = "排程提醒：進場前需求尚未確認";
  } else if (schedulingGateState === "allowed" && schedulingGateReason === "requirement_confirmed") {
    schedulingGateLabel = "可排程：進場前需求已確認";
  } else if (schedulingGateState === "allowed" && schedulingGateReason === "no_requirement") {
    schedulingGateLabel = "可排程：無進場前需求";
  }

  return {
    schedulingGateState,
    schedulingGateReason,
    schedulingGateLabel,
  };
}

function buildCrewFormalApproveMeta(entry) {
  return {
    actionLabel: "正式核准",
    successMessage: "已完成正式核准",
    blockedMessage: "無法完成正式核准：進場前需求尚未確認",
    actionMarkup: `<button type="button" class="crew-formal-approve-btn" data-testid="crew-work-entry-formal-approve-action" data-entry-id="${escapeHtml(entry?.id ?? "")}" data-sheet-id="${escapeHtml(entry?.sheet_id ?? "")}">正式核准</button>`,
  };
}

function buildCrewFormalApprovalIndicatorMeta(entry) {
  const formalApprovalState = String(entry?.formal_approval_state || "pending").trim() || "pending";
  const formalApprovalStatus = String(entry?.formal_approval_status || "pending").trim() || "pending";
  const formalApprovedBy = String(entry?.formal_approved_by || "").trim();
  const formalApprovedAt = String(entry?.formal_approved_at || "").trim();
  const indicatorLabel = formalApprovalState === "approved" ? "正式核准：已完成" : "正式核准：待核准";
  const detailMarkup =
    formalApprovalState === "approved" && (formalApprovedBy || formalApprovedAt)
      ? `<div data-testid="crew-work-entry-formal-approval-meta"><span class="crew-label">核准資訊</span><strong data-testid="crew-work-entry-formal-approved-by">${escapeHtml(formalApprovedBy || "已完成正式核准")}</strong>${formalApprovedAt ? `<span data-testid="crew-work-entry-formal-approved-at">${escapeHtml(formatCrewDateTime(formalApprovedAt))}</span>` : ""}</div>`
      : "";
  return {
    formalApprovalState,
    formalApprovalStatus,
    formalApprovedBy,
    formalApprovedAt,
    indicatorLabel,
    detailMarkup,
  };
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
              .map((entry) => {
                const requirementMeta = buildCrewRequirementMeta(entry);
                return `
          <div class="crew-entry-row">
            <div><span class="crew-label">預計進場</span><strong>${escapeHtml(formatCrewDateTime(entry.planned_at || "")) || "—"}</strong></div>
            <div><span class="crew-label">預計進場人數</span><strong>${escapeHtml(entry.planned_headcount ?? 0)}</strong></div>
            <div><span class="crew-label">實際進場人數</span><strong>${escapeHtml(entry.actual_headcount ?? 0)}</strong></div>
            <div><span class="crew-label">施作內容</span><strong>${escapeHtml(entry.work_content || "—")}</strong></div>
            <div><span class="crew-label">各項目施作人數</span><strong>${escapeHtml(entry.work_headcount ?? 0)}</strong></div>
          </div>
        `;
              })
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

  const vendorCards = crewVendorList.querySelectorAll(".crew-vendor-card");
  vendors.forEach((vendor, vendorIndex) => {
    const entryRows = vendorCards[vendorIndex]?.querySelectorAll(".crew-entry-row") || [];
    const entries = Array.isArray(vendor.work_entries) ? vendor.work_entries : [];
    entries.forEach((entry, entryIndex) => {
      const row = entryRows[entryIndex];
      if (!row) return;
      const requirementMeta = buildCrewRequirementMeta(entry);
      const readinessMeta = buildCrewReadinessMeta(entry);
      const schedulingGateMeta = buildCrewSchedulingGateMeta(entry);
      const formalApprovalIndicatorMeta = buildCrewFormalApprovalIndicatorMeta(entry);
      const formalApproveMeta = buildCrewFormalApproveMeta(entry);

      row.setAttribute("data-work-hub-entry", "today-entry");
      if (schedulingGateMeta.schedulingGateState === "warning") {
        row.setAttribute("data-work-hub-blocked", "true");
      }
      if (
        schedulingGateMeta.schedulingGateState === "allowed" &&
        formalApprovalIndicatorMeta.formalApprovalState === "pending"
      ) {
        row.setAttribute("data-work-hub-pending-approval", "true");
      }
      if (readinessMeta.readinessReason === "requirement_pending") {
        row.setAttribute("data-work-hub-pending-requirement", "true");
      }

      const requirementNode = document.createElement("div");
      requirementNode.setAttribute("data-testid", "crew-work-entry-pre-entry-requirement");
      requirementNode.innerHTML = `<span class="crew-label">進場前需求</span><strong>${escapeHtml(requirementMeta.requirementDisplay)}</strong>`;
      row.appendChild(requirementNode);

      const statusNode = document.createElement("div");
      statusNode.setAttribute("data-testid", "crew-work-entry-requirement-status");
      statusNode.innerHTML = `<span class="crew-label">需求確認狀態</span><strong>${escapeHtml(requirementMeta.requirementStatus)}</strong>`;
      row.appendChild(statusNode);

      const readinessNode = document.createElement("div");
      readinessNode.setAttribute("data-testid", "crew-work-entry-readiness-indicator");
      readinessNode.setAttribute("data-readiness-state", readinessMeta.readinessState);
      readinessNode.setAttribute("data-readiness-reason", readinessMeta.readinessReason);
      readinessNode.innerHTML = `<span class="crew-label">進場條件</span><strong>${escapeHtml(readinessMeta.readinessLabel)}</strong>`;
      row.appendChild(readinessNode);

      if (schedulingGateMeta.schedulingGateLabel) {
        const schedulingGateNode = document.createElement("div");
        schedulingGateNode.setAttribute("data-testid", "crew-work-entry-scheduling-gate-indicator");
        schedulingGateNode.setAttribute("data-scheduling-gate-state", schedulingGateMeta.schedulingGateState);
        schedulingGateNode.setAttribute("data-scheduling-gate-reason", schedulingGateMeta.schedulingGateReason);
        schedulingGateNode.innerHTML = `<span class="crew-label">排程提醒</span><strong>${escapeHtml(schedulingGateMeta.schedulingGateLabel)}</strong>`;
        row.appendChild(schedulingGateNode);
      }

      const formalApprovalNode = document.createElement("div");
      formalApprovalNode.setAttribute("data-testid", "crew-work-entry-formal-approval-indicator");
      formalApprovalNode.setAttribute("data-formal-approval-state", formalApprovalIndicatorMeta.formalApprovalState);
      formalApprovalNode.setAttribute("data-formal-approval-status", formalApprovalIndicatorMeta.formalApprovalStatus);
      formalApprovalNode.innerHTML = `<span class="crew-label">正式核准</span><strong>${escapeHtml(formalApprovalIndicatorMeta.indicatorLabel)}</strong>`;
      row.appendChild(formalApprovalNode);

      if (formalApprovalIndicatorMeta.detailMarkup) {
        const formalApprovalMetaNode = document.createElement("div");
        formalApprovalMetaNode.innerHTML = formalApprovalIndicatorMeta.detailMarkup;
        row.appendChild(formalApprovalMetaNode.firstElementChild);
      }

      if (requirementMeta.confirmedMeta) {
        const confirmedMetaNode = document.createElement("div");
        confirmedMetaNode.innerHTML = requirementMeta.confirmedMeta;
        row.appendChild(confirmedMetaNode.firstElementChild);
      }

      const actionSlot = document.createElement("div");
      actionSlot.setAttribute("data-testid", "crew-work-entry-requirement-action-slot");
      actionSlot.innerHTML = requirementMeta.actionMarkup;
      row.appendChild(actionSlot);

      const formalApproveSlot = document.createElement("div");
      formalApproveSlot.setAttribute("data-testid", "crew-work-entry-formal-approve-slot");
      formalApproveSlot.innerHTML = `${formalApproveMeta.actionMarkup}<div data-testid="crew-work-entry-formal-approve-feedback"></div>`;
      row.appendChild(formalApproveSlot);
    });
  });
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

async function confirmCrewWorkEntryRequirement(button) {
  const entryId = Number.parseInt(button?.dataset.entryId || "", 10);
  const sheetId = Number.parseInt(button?.dataset.sheetId || crewFormShell?.dataset.sheetId || "", 10);
  if (!entryId || !sheetId) {
    renderCrewFormError("缺少 requirement confirm context。");
    return;
  }

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "確認中...";
  try {
    const response = await fetch("/api/crew-work-entry-requirement-confirm", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        entry_id: entryId,
        sheet_id: sheetId,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) {
      throw new Error(data?.error?.message || "crew requirement confirmation failed");
    }
    await loadCrewForms(sheetId);
  } catch (error) {
    button.disabled = false;
    button.textContent = originalText;
    renderCrewFormError(error?.message || "crew requirement confirmation failed");
  }
}

async function loadCrewWorkHubSummary(sheetId) {
  if (!crewWorkHubCards || !sheetId) return;
  try {
    const response = await fetch(`/api/dashboard?sheet_id=${encodeURIComponent(sheetId)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data?.summary) {
      throw new Error(data?.error?.message || "dashboard summary request failed");
    }
    renderCrewWorkHubCards(data);
  } catch {
    renderCrewWorkHubCards({
      summary: {
        blocked_count: 0,
        pending_approval_count: 0,
        pending_requirement_count: 0,
        today_entry_count: 0,
      },
    });
  }
}

function setCrewFormalApproveFeedback(button, message, state = "") {
  const slot = button?.closest("[data-testid='crew-work-entry-formal-approve-slot']");
  const feedback = slot?.querySelector("[data-testid='crew-work-entry-formal-approve-feedback']");
  if (!feedback) return;
  feedback.textContent = message || "";
  if (state) {
    feedback.setAttribute("data-feedback-state", state);
  } else {
    feedback.removeAttribute("data-feedback-state");
  }
}

async function approveCrewWorkEntryFormal(button) {
  const entryId = Number.parseInt(button?.dataset.entryId || "", 10);
  const sheetId = Number.parseInt(button?.dataset.sheetId || crewFormShell?.dataset.sheetId || "", 10);
  if (!entryId || !sheetId) {
    renderCrewFormError("missing formal approve context");
    return;
  }

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "核准中...";
  setCrewFormalApproveFeedback(button, "");
  try {
    const response = await fetch("/api/crew-work-entry/formal-approve", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        entry_id: entryId,
        sheet_id: sheetId,
        action: "crew_formal_approve_entry",
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) {
      if (data?.error?.code === "entry_not_ready") {
        setCrewFormalApproveFeedback(button, "無法完成正式核准：進場前需求尚未確認", "blocked");
        return;
      }
      throw new Error(data?.error?.message || "crew formal approve failed");
    }
    setCrewFormalApproveFeedback(button, "已完成正式核准", "success");
  } catch (error) {
    setCrewFormalApproveFeedback(button, error?.message || "crew formal approve failed", "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
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

  const crewWorkHubCard = event.target.closest("[data-work-hub-action]");
  if (crewWorkHubCard) return scrollCrewWorkHubToTarget(crewWorkHubCard.dataset.workHubAction);

  const crewRequirementConfirm = event.target.closest("[data-testid='crew-work-entry-requirement-confirm-action']");
  if (crewRequirementConfirm) return confirmCrewWorkEntryRequirement(crewRequirementConfirm);

  const crewFormalApprove = event.target.closest("[data-testid='crew-work-entry-formal-approve-action']");
  if (crewFormalApprove) return approveCrewWorkEntryFormal(crewFormalApprove);

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
  loadCrewWorkHubSummary(crewFormShell.dataset.sheetId);
  loadCrewForms(crewFormShell.dataset.sheetId);
}
setInterval(refreshGrid, 10000);
