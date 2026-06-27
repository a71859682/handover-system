const ADMIN_SCROLL_KEY = "tableAdminScrollY";
const ADMIN_OPEN_FLOORS_KEY = "tableAdminOpenFloors";
const ADMIN_OPEN_LAST_FLOOR_KEY = "tableAdminOpenLastFloor";

function saveAdminView(submitter = null) {
  sessionStorage.setItem(ADMIN_SCROLL_KEY, String(window.scrollY));
  const openFloors = [...document.querySelectorAll(".floor-edit[open][data-floor-id]")]
    .map((detail) => detail.dataset.floorId);
  sessionStorage.setItem(ADMIN_OPEN_FLOORS_KEY, JSON.stringify(openFloors));

  if (submitter?.matches('[name="action"][value="add_floor"]')) {
    sessionStorage.setItem(ADMIN_OPEN_LAST_FLOOR_KEY, "1");
  }
}

document.addEventListener("submit", (event) => {
  saveAdminView(event.submitter);
});

document.addEventListener("click", (event) => {
  const anchor = event.target.closest("a");
  if (!anchor) return;
  saveAdminView();
});

window.addEventListener("load", () => {
  const openFloorsValue = sessionStorage.getItem(ADMIN_OPEN_FLOORS_KEY);
  if (openFloorsValue) {
    sessionStorage.removeItem(ADMIN_OPEN_FLOORS_KEY);
    try {
      const openFloors = new Set(JSON.parse(openFloorsValue));
      document.querySelectorAll(".floor-edit[data-floor-id]").forEach((detail) => {
        detail.open = openFloors.has(detail.dataset.floorId);
      });
    } catch {
      sessionStorage.removeItem(ADMIN_OPEN_FLOORS_KEY);
    }
  }

  if (sessionStorage.getItem(ADMIN_OPEN_LAST_FLOOR_KEY)) {
    sessionStorage.removeItem(ADMIN_OPEN_LAST_FLOOR_KEY);
    const details = document.querySelectorAll(".floor-edit[data-floor-id]");
    const last = details[details.length - 1];
    if (last) last.open = true;
  }

  const value = sessionStorage.getItem(ADMIN_SCROLL_KEY);
  if (!value) return;
  sessionStorage.removeItem(ADMIN_SCROLL_KEY);
  const target = Number(value) || 0;
  [0, 50, 150, 300].forEach((delay) => {
    window.setTimeout(() => window.scrollTo(0, target), delay);
  });
});
