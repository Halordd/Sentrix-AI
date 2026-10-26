import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const APP_URL = process.env.APP_URL ?? "http://10.20.10.10/";
const CDP_PORT = Number(process.env.CDP_PORT ?? 9402);
const BROWSERS = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome",
].filter(Boolean);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.id = 0;
    this.pending = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message));
        else resolve(message.result);
      }
    });
  }
  static connect(url) {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(url);
      socket.addEventListener("open", () => resolve(new Cdp(socket)));
      socket.addEventListener("error", () => reject(new Error("CDP websocket error")));
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  }
  close() { try { this.socket.close(); } catch { /* closed */ } }
}

async function waitFor(predicate, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await sleep(100);
  }
  throw new Error(`timed out waiting for ${label}`);
}

async function main() {
  const login = await fetch("http://10.20.10.10/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "maya@sentrix.local", password: "sentrix-demo" }),
  });
  if (!login.ok) throw new Error(`login failed: HTTP ${login.status}`);
  const { token } = await login.json();
  const origin = new URL(APP_URL).origin;

  const executable = BROWSERS.find((candidate) => existsSync(candidate));
  if (!executable) throw new Error("no Chromium-based browser found");
  const profile = await mkdtemp(join(tmpdir(), "sentrix-ui-"));
  const child = spawn(executable, [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
    "--no-first-run",
    "--user-data-dir=" + profile,
    "--remote-debugging-port=" + CDP_PORT,
    "about:blank",
  ], { stdio: "ignore" });

  let cdp;
  try {
    await waitFor(async () => {
      if (child.exitCode !== null) throw new Error(`browser exited (${child.exitCode})`);
      const response = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`).catch(() => null);
      return response?.ok === true;
    }, 20000, "devtools");

    const created = await fetch(
      `http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(APP_URL)}`,
      { method: "PUT" },
    );
    if (!created.ok) throw new Error(`target failed: ${created.status}`);
    const target = await created.json();
    cdp = await Cdp.connect(target.webSocketDebuggerUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Page.navigate", { url: origin + "/login.html" });
    await waitFor(
      async () => (await cdp.evaluate("document.readyState")) === "complete",
      15000,
      "login page",
    );
    await cdp.evaluate(
      `localStorage.setItem('sentrix_token', ${JSON.stringify(token)})`,
    );
    await cdp.send("Page.navigate", { url: APP_URL });
    await waitFor(
      async () => (await cdp.evaluate("document.querySelector('.brand b')?.textContent")) === "SENTRIX",
      15000,
      "SENTRIX shell",
    );
    await waitFor(
      async () => (await cdp.evaluate("document.body.innerText")).includes("Atlas Commerce"),
      15000,
      "API data",
    );
    console.log("PASS overview data");

    const views = [
      ["projects", "Atlas Commerce"],
      ["scans", "External perimeter review"],
      ["findings", "Broken object-level authorization"],
      ["intelligence", "Mock inference"],
      ["attack", "api.atlas.example"],
      ["reports", "Atlas Commerce — Security assessment"],
      ["models", "SENTRIX Risk Engine"],
      ["settings", "Published report"],
    ];
    for (const [view, marker] of views) {
      await cdp.evaluate(`document.querySelector('[data-view="${view}"]')?.click()`);
      await sleep(250);
      const text = await cdp.evaluate("document.body.innerText");
      if (!text.includes(marker)) throw new Error(`${view} missing marker: ${marker} :: ${text.slice(0, 1200)}`);
      console.log(`PASS ${view}`);
    }
    console.log("UI_SMOKE_PASSED");
  } finally {
    if (cdp) {
      try { await cdp.send("Browser.close"); } catch { /* closed */ }
      cdp.close();
    }
    if (child.exitCode === null) child.kill();
    await rm(profile, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch((error) => {
  console.error("UI_SMOKE_FAILED", error.message);
  process.exit(1);
});
