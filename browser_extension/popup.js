const labels = {
  free: "Free",
  plus: "Plus",
  team: "Team",
  pro: "Pro"
};

function renderModels(models) {
  const root = document.getElementById("models");
  root.textContent = "";

  models.forEach((model) => {
    const row = document.createElement("div");
    row.className = "row";

    const label = document.createElement("div");
    label.className = "label";
    label.textContent = `${model.id} · ${model.used}/${model.quota}`;

    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("div");
    fill.className = "fill";
    const denom = model.quota > 0 ? model.quota : (model.max || 1);
    fill.style.width = `${Math.min(100, Math.max(0, (model.used / denom) * 100))}%`;
    bar.appendChild(fill);

    row.appendChild(label);
    row.appendChild(bar);
    root.appendChild(row);
  });
}

function setActivePlan(plan) {
  document.querySelectorAll(".plans button").forEach((button) => {
    button.textContent = labels[button.dataset.plan];
    button.classList.toggle("active", button.dataset.plan === plan);
  });
}

function refresh() {
  chrome.runtime.sendMessage({ action: "getUsageData" }, (response) => {
    if (!response) {
      return;
    }
    setActivePlan(response.plan || "plus");
    renderModels(response.models || []);
  });
}

document.querySelector(".plans").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }
  chrome.runtime.sendMessage({ action: "setActivePlan", plan: button.dataset.plan }, refresh);
});

document.getElementById("sync").addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "syncNow" }, refresh);
});

refresh();
