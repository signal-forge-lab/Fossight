import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const registryPath = path.join(moduleDir, "oss-registry.json");
const desktopScript = path.join(moduleDir, "desktop.ps1");
const desktopExe = path.join(moduleDir, "src-tauri", "target", "release", "oss-update-watch-desktop.exe");

function respond(payload) {
  process.stdout.write(JSON.stringify(payload));
}

async function readRequest() {
  let text = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) text += chunk;
  return JSON.parse(text);
}

function registrySummary() {
  try {
    const registry = JSON.parse(fs.readFileSync(registryPath, "utf8"));
    const items = Array.isArray(registry.items) ? registry.items : [];
    return {
      registered: items.length,
      enabled: items.filter((item) => item.enabled !== false).length,
      disabled: items.filter((item) => item.enabled === false).length,
    };
  } catch {
    return { registered: 0, enabled: 0, disabled: 0 };
  }
}

function desktopRunning() {
  if (process.platform === "win32") {
    const result = spawnSync(
      "tasklist.exe",
      ["/FI", "IMAGENAME eq oss-update-watch-desktop.exe", "/FO", "CSV", "/NH"],
      { encoding: "utf8", windowsHide: true },
    );
    return result.status === 0 && result.stdout.toLowerCase().includes("oss-update-watch-desktop.exe");
  }
  const result = spawnSync("pgrep", ["-f", "oss-update-watch-desktop"], { encoding: "utf8" });
  return result.status === 0 && result.stdout.trim().length > 0;
}

function spawnDetached(command, args) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: moduleDir,
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    });
    child.once("error", (error) => resolve({ ok: false, message: `Unable to launch desktop app: ${error.message}` }));
    child.once("spawn", () => {
      child.unref();
      resolve({ ok: true, message: "Opening Fossight" });
    });
  });
}

async function openDesktop() {
  if (desktopRunning()) {
    return { ok: true, message: "Fossight is already open" };
  }
  if (process.platform !== "win32") {
    return { ok: false, message: "The desktop launcher is currently configured for Windows" };
  }
  if (fs.existsSync(desktopExe)) {
    return spawnDetached(desktopExe, []);
  }
  return spawnDetached("pwsh.exe", ["-NoProfile", "-File", desktopScript]);
}

const input = await readRequest();
if (input.protocol !== "modora.adapter/v1") {
  respond({ ok: false, message: "Unsupported protocol" });
  process.exit(0);
}

if (input.action === "status") {
  const running = desktopRunning();
  const summary = registrySummary();
  respond({
    ok: true,
    state: running ? "RUNNING" : "READY",
    detail: running
      ? "Desktop window is open"
      : fs.existsSync(desktopExe)
        ? "Desktop shell is built and ready"
        : "Desktop shell will be built on first open",
    updatedAt: new Date().toISOString(),
    signals: [
      { id: "registered", label: "Registered", value: String(summary.registered), detail: "OSS entries" },
      { id: "enabled", label: "Enabled", value: String(summary.enabled), detail: "checked for updates" },
      { id: "disabled", label: "Disabled", value: String(summary.disabled), detail: "retained but skipped" }
    ],
    quickView: [],
    activity: []
  });
  process.exit(0);
}

if (input.action === "open") {
  respond(await openDesktop());
  process.exit(0);
}

respond({ ok: false, message: `Unsupported action: ${input.action}` });
