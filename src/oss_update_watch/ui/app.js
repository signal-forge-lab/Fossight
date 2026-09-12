"use strict";

const state = {
  data: null,
  status: "all",
  relation: null,
  search: "",
  busy: false,
  selectedRepo: null,
  detailsOpen: false,
};
const $ = (id) => document.getElementById(id);

const labels = {
  up_to_date: "Watching",
  update_available: "Changed",
  unbaselined: "Baseline pending",
  error: "Error",
  disabled: "Disabled",
};

const localLabels = {
  latest: "Latest",
  behind: "Update",
  ahead: "Ahead",
  diverged: "Diverged",
  unavailable: "N/A",
  error: "Error",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function showToast(message, isError = false) {
  const toast = $("toast");
  toast.textContent = message;
  toast.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = "toast"; }, 2400);
}

function setBusy(busy, text = "") {
  state.busy = busy;
  $("checkButton").disabled = busy;
  $("ackButton").disabled = busy || !state.data || state.data.summary.upstream_changes === 0;
  $("busyText").textContent = busy ? text : "";
  document.querySelectorAll(".toggle").forEach((button) => { button.disabled = busy; });
  $("detailsToggle").disabled = busy || !state.selectedRepo;
}

function relationLabel(usages) {
  const relations = [...new Set(usages.map((usage) => usage.relation))];
  return relations.map((value) => value[0].toUpperCase() + value.slice(1)).join(" / ");
}

function trackingLabel(tracking) {
  if (tracking.mode === "auto") return "Auto";
  if (tracking.mode === "branch") return `Branch ${tracking.branch}`;
  return tracking.mode[0].toUpperCase() + tracking.mode.slice(1);
}

function currentLabel(item) {
  const current = item.current || {};
  return current.display || current.value || "—";
}

function usageSummary(item) {
  if (item.usages.length === 1) {
    const usage = item.usages[0];
    return [usage.project, usage.local_path].filter(Boolean).join(" · ");
  }
  return `${item.usages.length} usages · ${item.usages.map((usage) => usage.project).join(", ")}`;
}

function shortSummary(summary, limit = 94) {
  const value = String(summary || "").trim();
  if (!value) return "概要はまだ登録されていません。";
  return value.length > limit ? `${value.slice(0, limit).trim()}…` : value;
}

function selectedItem() {
  if (!state.data || !state.selectedRepo) return null;
  return state.data.items.find((item) => item.repo === state.selectedRepo) || null;
}

function usageDetailHtml(item) {
  const localByProject = new Map(
    (item.local?.usages || []).map((usage) => [usage.project, usage.local || {}]),
  );
  return item.usages.map((usage) => {
    const local = localByProject.get(usage.project) || {};
    const localState = local.status ? (localLabels[local.status] || local.status) : "N/A";
    return `
      <div class="usage-card">
        <div class="usage-card-head"><strong>${escapeHtml(usage.project)}</strong><span>${escapeHtml(usage.relation)}</span></div>
        <div class="usage-path">${escapeHtml(usage.local_path || "No local path")}</div>
        <div class="usage-state">Local: ${escapeHtml(localState)}</div>
      </div>`;
  }).join("");
}

function renderDetails() {
  const item = selectedItem();
  const panel = $("detailsPanel");
  panel.classList.toggle("drawer-open", Boolean(item && state.detailsOpen));
  $("detailsScrim").classList.toggle("show", Boolean(item && state.detailsOpen));
  $("detailsEmpty").hidden = Boolean(item);
  $("detailsContent").hidden = !item;
  if (!item) return;

  const local = item.local || { status: "unavailable" };
  $("detailsRepo").textContent = item.repo;
  $("detailsSummary").textContent = item.summary || "概要はまだ登録されていません。";
  $("detailsLocal").textContent = localLabels[local.status] || local.status || "N/A";
  $("detailsChange").textContent = labels[item.status] || item.status || "—";
  const homeLink = $("detailsHomeLink");
  homeLink.href = `https://github.com/${encodeURI(item.repo)}`;
  homeLink.title = `Open ${item.repo} on GitHub`;
  $("detailsTracking").textContent = trackingLabel(item.tracking);
  $("detailsCurrent").textContent = currentLabel(item);
  $("detailsPriority").textContent = item.priority || "normal";
  $("detailsUsages").innerHTML = usageDetailHtml(item);

  const toggle = $("detailsToggle");
  toggle.dataset.repo = item.repo;
  toggle.setAttribute("aria-checked", String(item.enabled));
  toggle.textContent = item.enabled ? "Enabled" : "Disabled";
  toggle.classList.toggle("on", item.enabled);
  toggle.disabled = state.busy;
}

function filteredItems() {
  if (!state.data) return [];
  const needle = state.search.trim().toLowerCase();
  return state.data.items.filter((item) => {
    if (state.status === "local_update" && !item.local?.update_available) return false;
    if (state.status === "upstream_change" && item.status !== "update_available") return false;
    if (state.status === "attention" && !["diverged", "error"].includes(item.local?.status)) return false;
    if (state.status === "error" && item.status !== "error" && item.local?.status !== "error") return false;
    if (state.status === "disabled" && item.status !== "disabled") return false;
    if (!["all", "local_update", "upstream_change", "attention", "error", "disabled"].includes(state.status)) return false;
    if (state.relation && !item.usages.some((usage) => usage.relation === state.relation)) return false;
    if (!needle) return true;
    const haystack = [
      item.repo,
      item.priority,
      item.tracking.mode,
      item.summary || "",
      ...item.usages.flatMap((usage) => [usage.project, usage.relation, usage.local_path || ""]),
    ].join(" ").toLowerCase();
    return haystack.includes(needle);
  });
}

function renderRows() {
  const list = $("repoList");
  const items = filteredItems();
  if (!items.length) {
    list.innerHTML = '<div class="empty"><div><strong>No matching OSS</strong><span>検索またはフィルタ条件を変更してください。</span></div></div>';
    return;
  }
  list.innerHTML = items.map((item) => {
    const repo = escapeHtml(item.repo);
    const enabled = item.enabled;
    const errorTitle = item.error ? ` title="${escapeHtml(item.error)}"` : "";
    const local = item.local || { status: "unavailable", usages: [] };
    const localTitle = local.usages?.length
      ? ` title="${escapeHtml(local.usages.map((usage) => `${usage.project}: ${usage.local?.status || "unavailable"}`).join(" · "))}"`
      : "";
    const selected = item.repo === state.selectedRepo;
    const tooltip = escapeHtml(shortSummary(item.summary));
    return `
      <div class="repo-row${selected ? " selected" : ""}" data-select-repo="${repo}">
        <button class="toggle${enabled ? " on" : ""}" type="button" role="switch" aria-checked="${enabled}" aria-label="${enabled ? "Disable" : "Enable"} ${repo}" data-repo="${repo}"></button>
        <div class="repo-main" tabindex="0" data-select-repo="${repo}" data-summary-tooltip="${tooltip}" aria-describedby="summaryTooltip"><div class="repo-name">${repo}</div><div class="repo-sub">${escapeHtml(usageSummary(item))}</div></div>
        <span class="type">${escapeHtml(relationLabel(item.usages))}</span>
        <span class="track">${escapeHtml(trackingLabel(item.tracking))}</span>
        <span class="version">${escapeHtml(currentLabel(item))}</span>
        <span class="local-status ${escapeHtml(local.status)}"${localTitle}>${escapeHtml(localLabels[local.status] || local.status)}</span>
        <span class="status ${escapeHtml(item.status)}"${errorTitle}>${escapeHtml(labels[item.status] || item.status)}</span>
      </div>`;
  }).join("");
  if (state.busy) document.querySelectorAll(".toggle").forEach((button) => { button.disabled = true; });
}

function render() {
  if (!state.data) return;
  const summary = state.data.summary;
  $("metricRegistered").textContent = summary.registered;
  $("metricUpdates").textContent = summary.local_updates;
  $("metricUpstream").textContent = summary.upstream_changes;
  $("metricErrors").textContent = summary.error;
  $("countAll").textContent = summary.registered;
  $("countUpdates").textContent = summary.local_updates;
  $("countUpstream").textContent = summary.upstream_changes;
  $("countAttention").textContent = summary.local_attention;
  $("countErrors").textContent = summary.error;
  $("countDisabled").textContent = summary.disabled;
  $("footerErrors").textContent = summary.error;
  $("lastCheck").textContent = state.data.latest_check ? new Date(state.data.latest_check).toLocaleString() : "Never";
  $("ackButton").disabled = state.busy || summary.upstream_changes === 0;
  const titleMap = { all: "All OSS", local_update: "Local updates", upstream_change: "Upstream changes", attention: "Attention", error: "Errors", disabled: "Disabled" };
  $("viewTitle").textContent = titleMap[state.status] || "All OSS";

  document.querySelectorAll("[data-status]").forEach((button) => button.classList.toggle("active", button.dataset.status === state.status));
  document.querySelectorAll("[data-relation]").forEach((button) => button.classList.toggle("active", button.dataset.relation === state.relation));
  renderRows();
  renderDetails();
}

async function loadRegistry() {
  try {
    state.data = await api("/api/registry");
    if (!selectedItem() && state.data.items.length) state.selectedRepo = state.data.items[0].repo;
    render();
    fillMissingSummaries();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function toggleRepo(button) {
  const repo = button.dataset.repo;
  const enabled = button.getAttribute("aria-checked") !== "true";
  button.disabled = true;
  try {
    await api("/api/enabled", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo, enabled }),
    });
    showToast(`${repo}: ${enabled ? "enabled" : "disabled"}`);
    await loadRegistry();
  } catch (error) {
    showToast(error.message, true);
    button.disabled = false;
  }
}

function selectRepo(repo, openDrawer = true) {
  state.selectedRepo = repo;
  if (openDrawer) state.detailsOpen = true;
  renderRows();
  renderDetails();
}

function closeDetails() {
  if (window.matchMedia("(max-width: 1180px)").matches) {
    state.detailsOpen = false;
  } else {
    state.selectedRepo = null;
  }
  renderRows();
  renderDetails();
}

function showSummaryTooltip(anchor) {
  const tooltip = $("summaryTooltip");
  const text = anchor.dataset.summaryTooltip;
  if (!text) return;
  tooltip.textContent = text;
  tooltip.hidden = false;
  requestAnimationFrame(() => {
    const rect = anchor.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const left = Math.min(
      Math.max(12, rect.left),
      window.innerWidth - tooltipRect.width - 12,
    );
    const preferredTop = rect.bottom + 7;
    const top = preferredTop + tooltipRect.height <= window.innerHeight - 12
      ? preferredTop
      : Math.max(12, rect.top - tooltipRect.height - 7);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  });
}

function hideSummaryTooltip() {
  $("summaryTooltip").hidden = true;
}

function setDetailsWidth(width) {
  const clamped = Math.max(320, Math.min(460, width));
  document.documentElement.style.setProperty("--details-width", `${clamped}px`);
  localStorage.setItem("oss-watch-details-width", String(clamped));
}

function beginDetailsResize(event) {
  if (window.matchMedia("(max-width: 1180px)").matches) return;
  event.preventDefault();
  const startX = event.clientX;
  const startWidth = $("detailsPanel").getBoundingClientRect().width;
  document.body.classList.add("resizing-details");
  const move = (moveEvent) => setDetailsWidth(startWidth + (startX - moveEvent.clientX));
  const stop = () => {
    document.body.classList.remove("resizing-details");
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
    window.removeEventListener("pointercancel", stop);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
  window.addEventListener("pointercancel", stop);
}

async function checkUpdates() {
  setBusy(true, "Checking upstream + local…");
  try {
    state.data = await api("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    render();
    showToast("Update check completed");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function acknowledgeChanges() {
  setBusy(true, "Acknowledging upstream changes…");
  try {
    const payload = await api("/api/ack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    state.data = payload.dashboard;
    render();
    showToast(`Acknowledged ${payload.changed} upstream value(s)`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".toggle[data-repo]");
  if (toggle) { toggleRepo(toggle); return; }
  const row = event.target.closest("[data-select-repo]");
  if (row) { selectRepo(row.dataset.selectRepo); return; }
  const statusButton = event.target.closest("[data-status]");
  if (statusButton) { state.status = statusButton.dataset.status; render(); return; }
  const relationButton = event.target.closest("[data-relation]");
  if (relationButton) { state.relation = relationButton.dataset.relation; render(); return; }
});

document.addEventListener("pointerover", (event) => {
  const anchor = event.target.closest(".repo-main[data-summary-tooltip]");
  if (anchor && !anchor.contains(event.relatedTarget)) showSummaryTooltip(anchor);
});
document.addEventListener("pointerout", (event) => {
  const anchor = event.target.closest(".repo-main[data-summary-tooltip]");
  if (anchor && !anchor.contains(event.relatedTarget)) hideSummaryTooltip();
});
document.addEventListener("focusin", (event) => {
  const anchor = event.target.closest(".repo-main[data-summary-tooltip]");
  if (anchor) showSummaryTooltip(anchor);
});
document.addEventListener("focusout", (event) => {
  if (event.target.closest(".repo-main[data-summary-tooltip]")) hideSummaryTooltip();
});
document.addEventListener("keydown", (event) => {
  const row = event.target.closest(".repo-main[data-select-repo]");
  if (row && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    selectRepo(row.dataset.selectRepo);
  }
  if (event.key === "Escape" && state.detailsOpen) closeDetails();
});

$("searchInput").addEventListener("input", (event) => { state.search = event.target.value; renderRows(); });
$("refreshButton").addEventListener("click", loadRegistry);
$("checkButton").addEventListener("click", checkUpdates);
$("ackButton").addEventListener("click", acknowledgeChanges);
$("clearRelation").addEventListener("click", () => { state.relation = null; render(); });
$("detailsToggle").addEventListener("click", (event) => toggleRepo(event.currentTarget));
$("detailsClose").addEventListener("click", closeDetails);
$("detailsScrim").addEventListener("click", closeDetails);
$("detailsResizeHandle").addEventListener("pointerdown", beginDetailsResize);
$("detailsResizeHandle").addEventListener("keydown", (event) => {
  if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
  event.preventDefault();
  const width = $("detailsPanel").getBoundingClientRect().width;
  setDetailsWidth(width + (event.key === "ArrowLeft" ? 16 : -16));
});

const savedDetailsWidth = Number(localStorage.getItem("oss-watch-details-width"));
if (Number.isFinite(savedDetailsWidth) && savedDetailsWidth > 0) setDetailsWidth(savedDetailsWidth);

/* ------------------------------------------------------------------ *
 * Prerequisites + onboarding + scanner                                *
 * ------------------------------------------------------------------ */

const ob = {
  open: false,
  step: "welcome",
  settings: null,
  prereqs: null,
  roots: [],
  job: null,
  previewJob: null,
  pollTimer: null,
  rows: [],
  startedAutomatically: false,
};

function obShow(step) {
  ob.step = step;
  document.querySelectorAll(".ob-step").forEach((section) => {
    section.hidden = section.dataset.step !== step;
  });
  $("onboardingOverlay").hidden = !ob.open;
}

async function loadPrereqs() {
  try {
    ob.prereqs = await api("/api/prerequisites");
  } catch (error) {
    ob.prereqs = null;
  }
  renderPrereqUi();
}

function renderPrereqUi() {
  const chip = $("prereqChip");
  const banner = $("prereqBanner");
  const git = ob.prereqs?.git;
  const auth = ob.prereqs?.github_auth;
  if (git?.available) {
    chip.hidden = false;
    chip.textContent = `Git ready`;
    chip.className = "prereq-chip ok";
    chip.title = git.version || "Git is available";
    banner.hidden = true;
  } else if (git) {
    chip.hidden = false;
    chip.textContent = "Git missing";
    chip.className = "prereq-chip bad";
    banner.hidden = false;
    $("prereqBannerText").textContent = ob.prereqs.remediation || "Git not found.";
  }
  if (ob.open && ob.step === "prereqs") {
    const gitOk = Boolean(git?.available);
    $("obGitState").textContent = gitOk ? "Git: Ready" : "Git: Missing";
    $("obGitState").className = `ob-state ${gitOk ? "ok" : "bad"}`;
    $("obGitVersion").textContent = git?.version || "";
    const source = auth?.source || "anonymous";
    const authLabel = source === "anonymous" ? "GitHub: anonymous" : `GitHub: authenticated via ${source}`;
    $("obAuthState").textContent = authLabel;
    $("obAuthState").className = `ob-state ${auth?.authenticated ? "ok" : "warn"}`;
    $("obAuthNote").textContent = auth?.note || "";
    $("obGitRemediation").hidden = gitOk;
    $("obGitRemediation").textContent = gitOk ? "" : ob.prereqs?.remediation || "";
    $("obPrereqNext").disabled = false;
    if (gitOk) $("obPrereqNext").textContent = "Continue";
  }
}

async function loadSettings() {
  try {
    const payload = await api("/api/settings");
    ob.settings = payload.config;
  } catch (error) {
    ob.settings = null;
  }
}

async function maybeStartOnboarding() {
  if (ob.startedAutomatically) return;
  ob.startedAutomatically = true;
  await loadSettings();
  const empty = !state.data || state.data.summary.registered === 0;
  const complete = Boolean(ob.settings?.onboarding_complete);
  if (empty && !complete) openOnboarding("welcome");
}

function openOnboarding(step) {
  ob.open = true;
  obShow(step);
  if (step === "prereqs" && !ob.prereqs) loadPrereqs();
  if (step === "folders") {
    ob.roots = ((ob.settings?.scan_roots) || []).map((root) => ({ path: root.path, mode: root.mode || "quick" }));
    renderObRoots();
    ob.prereqs ? renderPrereqUi() : loadPrereqs();
  }
}

function closeOnboarding() {
  ob.open = false;
  stopPolling();
  obShow(ob.step);
  $("onboardingOverlay").hidden = true;
}

function renderObRoots() {
  const list = $("obRootList");
  if (!ob.roots.length) {
    list.innerHTML = '<p class="ob-empty">No folders selected yet.</p>';
  } else {
    list.innerHTML = ob.roots.map((root, index) => `
      <div class="ob-root-row">
        <span class="ob-root-path" title="${escapeHtml(root.path)}">${escapeHtml(root.path)}</span>
        <select class="ob-root-mode" data-index="${index}" aria-label="Scan mode for ${escapeHtml(root.path)}">
          <option value="quick"${root.mode === "quick" ? " selected" : ""}>Quick Scan</option>
          <option value="deep"${root.mode === "deep" ? " selected" : ""}>Deep Scan</option>
        </select>
        <button class="ob-root-remove" data-index="${index}" type="button" aria-label="Remove ${escapeHtml(root.path)}">×</button>
      </div>`).join("");
  }
  $("obScanStart").disabled = ob.roots.length === 0;
}

async function persistObRoots() {
  if (!ob.settings) await loadSettings();
  if (!ob.settings) return;
  ob.settings.scan_roots = ob.roots.map((root) => ({ path: root.path, mode: root.mode, enabled: true }));
  try {
    const payload = await api("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: ob.settings }),
    });
    ob.settings = payload.config;
  } catch (error) {
    showToast(error.message, true);
  }
}

async function addObFolder() {
  let path = null;
  try {
    const payload = await api("/api/pick-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    path = payload.path;
    if (!payload.available && !path) {
      $("obManualPath").hidden = false;
      $("obAddManual").hidden = false;
    }
  } catch (error) {
    $("obManualPath").hidden = false;
    $("obAddManual").hidden = false;
  }
  if (path) {
    if (!ob.roots.some((root) => root.path.toLowerCase() === path.toLowerCase())) {
      ob.roots.push({ path, mode: "quick" });
      await persistObRoots();
    }
    renderObRoots();
  }
}

async function addObManualPath() {
  const input = $("obManualPath");
  const value = input.value.trim();
  if (!value) return;
  if (!ob.roots.some((root) => root.path.toLowerCase() === value.toLowerCase())) {
    ob.roots.push({ path: value, mode: "quick" });
    await persistObRoots();
  }
  input.value = "";
  renderObRoots();
}

function startScan() {
  if (!ob.roots.length) return;
  persistObRoots();
  obShow("scanning");
  $("obScanProgress").textContent = "Preparing scan…";
  fetch("/api/scan/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({ roots: ob.roots.map((root) => ({ path: root.path, mode: root.mode })) }),
  })
    .then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      ob.job = payload.job;
      pollScan();
    })
    .catch((error) => {
      showToast(error.message, true);
      obShow("folders");
    });
}

function stopPolling() {
  if (ob.pollTimer) clearTimeout(ob.pollTimer);
  ob.pollTimer = null;
}

function pollScan() {
  if (!ob.job) return;
  stopPolling();
  ob.pollTimer = setTimeout(async () => {
    try {
      const status = await api(`/api/scan/status?job=${encodeURIComponent(ob.job)}`);
      $("obScanProgress").textContent =
        `Scanned ${status.progress.directories_seen} folders · found ${status.progress.repositories_found} Git repositories…`;
      if (status.running) { pollScan(); return; }
      if (status.error) throw new Error(status.error);
      ob.rows = status.rows || [];
      ob.previewJob = ob.job;
      ob.job = null;
      renderPreview(status.counts || {});
    } catch (error) {
      showToast(error.message, true);
      obShow("folders");
    }
  }, 400);
}

async function cancelScan() {
  stopPolling();
  const job = ob.job;
  ob.job = null;
  if (job) {
    try {
      await api("/api/scan/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job }),
      });
    } catch { /* job may already be finished */ }
  }
  obShow("folders");
}

function renderPreview(counts) {
  const supported = counts.supported ?? ob.rows.filter((row) => row.status === "ok").length;
  const found = counts.repositories_found ?? ob.rows.length;
  $("obPreviewCounts").textContent = `Found ${found} Git repositories · ${supported} supported GitHub repositories`;
  const list = $("obPreviewList");
  if (!ob.rows.length) {
    list.innerHTML = '<p class="ob-empty">No Git repositories found in the selected folders.</p>';
  } else {
    list.innerHTML = ob.rows.map((row, index) => {
      const ok = row.status === "ok";
      const badges = [
        ok ? escapeHtml(row.relation) : "skipped",
        ok ? `via ${escapeHtml(row.remote_source)}` : "",
        row.already_registered ? "already registered" : "",
      ].filter(Boolean).join(" · ");
      const reason = row.reason ? ` title="${escapeHtml(row.reason)}"` : "";
      return `
        <div class="ob-preview-row${ok ? "" : " skipped"}"${reason}>
          <input type="checkbox" class="ob-select" data-index="${index}" ${row.selected ? "checked" : ""} ${ok ? "" : "disabled"} aria-label="Select ${escapeHtml(row.project)}">
          <div class="ob-preview-main">
            <div class="ob-preview-name">${escapeHtml(ok ? row.repo : row.project)}</div>
            <div class="ob-preview-path">${escapeHtml(row.local_path)}</div>
          </div>
          <span class="ob-preview-meta">${badges}</span>
        </div>`;
    }).join("");
  }
  updateApplyCount();
  obShow("preview");
}

function selectedPreviewPaths() {
  return Array.from(document.querySelectorAll(".ob-select:checked"))
    .map((box) => ob.rows[Number(box.dataset.index)]?.local_path)
    .filter(Boolean);
}

function updateApplyCount() {
  const count = selectedPreviewPaths().length;
  const button = $("obApplySelected");
  button.disabled = count === 0;
  button.textContent = `Add selected (${count})`;
}

async function applySelected() {
  const paths = selectedPreviewPaths();
  const job = ob.previewJob;
  if (!paths.length || !job) return;
  const button = $("obApplySelected");
  button.disabled = true;
  try {
    const payload = await api("/api/scan/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job, local_paths: paths }),
    });
    state.data = payload.dashboard;
    render();
    $("obDoneMessage").textContent =
      payload.applied.length
        ? `Added ${payload.applied.length} repositor${payload.applied.length === 1 ? "y" : "ies"}. Run your first update check from the main window.`
        : "Selections were already registered. You're ready to use Fossight.";
    obShow("done");
    ob.settings && (ob.settings.onboarding_complete = true);
  } catch (error) {
    showToast(error.message, true);
    obShow("preview");
    button.disabled = false;
  }
}

async function finishOnboarding() {
  closeOnboarding();
  await loadRegistry();
}

async function fillMissingSummaries() {
  if (!state.data) return;
  const missing = state.data.items.filter((item) => !item.summary).slice(0, 30);
  for (const item of missing) {
    try {
      const meta = await api(`/api/repository-metadata?repo=${encodeURIComponent(item.repo)}`);
      if (meta.summary && meta.source !== "none") {
        item.summary = meta.summary;
        renderRows();
        renderDetails();
      }
    } catch { /* offline or unknown: keep empty summary */ }
  }
}

document.addEventListener("click", (event) => {
  const remove = event.target.closest(".ob-root-remove");
  if (remove) {
    ob.roots.splice(Number(remove.dataset.index), 1);
    persistObRoots();
    renderObRoots();
    return;
  }
});
document.addEventListener("change", (event) => {
  const mode = event.target.closest(".ob-root-mode");
  if (mode) {
    ob.roots[Number(mode.dataset.index)].mode = mode.value;
    persistObRoots();
    return;
  }
  if (event.target.classList?.contains("ob-select")) updateApplyCount();
});

$("obGetStarted").addEventListener("click", () => { obShow("prereqs"); loadPrereqs(); });
$("obPrereqRetry").addEventListener("click", loadPrereqs);
$("obPrereqNext").addEventListener("click", () => openOnboarding("folders"));
$("obAddFolder").addEventListener("click", addObFolder);
$("obAddManual").addEventListener("click", addObManualPath);
$("obCloseFolders").addEventListener("click", closeOnboarding);
$("obManualPath").addEventListener("keydown", (event) => {
  if (event.key === "Enter") addObManualPath();
});
$("obScanStart").addEventListener("click", startScan);
$("obScanCancel").addEventListener("click", cancelScan);
$("obPreviewBack").addEventListener("click", () => obShow("folders"));
$("obApplySelected").addEventListener("click", applySelected);
$("obFinish").addEventListener("click", finishOnboarding);
$("scannerButton").addEventListener("click", () => { loadSettings().then(() => openOnboarding("folders")); });
$("prereqBannerRetry").addEventListener("click", loadPrereqs);

loadRegistry().then(() => { loadPrereqs(); maybeStartOnboarding(); });
