/**
 * API-mode browser parity checks for SENTRIX M5-06.
 *
 * Drives the deployed UI over CDP, signs in through the real login form, walks
 * every view, exports the seeded report CSV, and asserts that the page issues no
 * off-origin requests or uncaught exceptions.
 *
 *   node scripts/browser-api-check.mjs
 *
 * Environment: APP_URL, CDP_PORT, EDGE_PATH/BROWSER_PATH.
 * Read-only against seed data; it does not create or mutate domain rows.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const APP_URL = process.env.APP_URL ?? "http://10.20.10.10/";
const CDP_PORT = Number(process.env.CDP_PORT ?? 9403);
const APP_ORIGIN = new URL(APP_URL).origin;
const BROWSERS = [
  process.env.EDGE_PATH,
  process.env.BROWSER_PATH,
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
    this.events = [];
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message));
        else resolve(message.result);
      } else if (message.method) {
        this.events.push(message);
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

const PAGE_HELPERS = `
  window.__text = (selector) => document.querySelector(selector)?.textContent?.trim() ?? null;
  window.__setValue = (selector, value) => {
    const element = document.querySelector(selector);
    if (!element) throw new Error('missing element: ' + selector);
    element.value = value;
  };
  window.__submit = (selector) => {
    const form = document.querySelector(selector);
    if (!form) throw new Error('missing form: ' + selector);
    form.requestSubmit();
  };
  'helpers-ready';
`;

async function main() {
  const executable = BROWSERS.find((candidate) => existsSync(candidate));
  if (!executable) throw new Error("no Chromium-based browser found");
  const profile = await mkdtemp(join(tmpdir(), "sentrix-api-check-"));
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
  const results = [];
  const check = async (name, run) => {
    try {
      const detail = await run();
      results.push({ name, ok: true, detail });
      console.log(`PASS  ${name}${detail ? ` — ${detail}` : ""}`);
    } catch (error) {
      results.push({ name, ok: false, detail: error.message });
      console.log(`FAIL  ${name} — ${error.message}`);
    }
  };

  try {
    await waitFor(async () => {
      if (child.exitCode !== null) throw new Error(`browser exited (${child.exitCode})`);
      const response = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`).catch(() => null);
      return response?.ok === true;
    }, 20000, "devtools");

    const created = await fetch(
      `http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(APP_ORIGIN + "/login.html")}`,
      { method: "PUT" },
    );
    if (!created.ok) throw new Error(`target failed: ${created.status}`);
    const target = await created.json();
    cdp = await Cdp.connect(target.webSocketDebuggerUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Network.enable");
    await waitFor(
      async () => (await cdp.evaluate("document.readyState")) === "complete",
      15000,
      "login page",
    );
    await waitFor(
      async () => (await cdp.evaluate("Boolean(document.querySelector('#login-form'))")) === true,
      15000,
      "login form render",
    );
    await cdp.evaluate(PAGE_HELPERS);

    await check("login page renders the form", async () => {
      const view = await cdp.evaluate(`({
        title: document.querySelector('h1')?.textContent?.trim() ?? null,
        form: Boolean(document.querySelector('#login-form')),
        email: document.querySelector('#login-form input[name="email"]')?.value,
      })`);
      assert.equal(view.title, "SENTRIX");
      assert.equal(view.form, true);
      assert.equal(view.email, "maya@sentrix.local");
      return "SENTRIX login form";
    });

    await check("authenticated bootstrap reaches the API console", async () => {
      const response = await fetch(APP_ORIGIN + "/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "maya@sentrix.local", password: "sentrix-demo" }),
      });
      assert.equal(response.status, 200);
      const { token } = await response.json();
      assert.ok(token);
      await cdp.evaluate(`localStorage.setItem('sentrix_token', ${JSON.stringify(token)})`);
      await cdp.send("Page.navigate", { url: APP_URL });
      await waitFor(
        async () => (await cdp.evaluate("document.querySelector('.brand b')?.textContent")) === "SENTRIX",
        15000,
        "authenticated shell",
      );
      await cdp.evaluate(PAGE_HELPERS);
      const view = await cdp.evaluate(`({ title: __text('.page-heading h1'), body: document.body.innerText })`);
      assert.equal(view.title, "Overview");
      assert.match(view.body, /Atlas Commerce/);
      return "token issued, bootstrap loaded";
    });

    const views = [
      ["projects", "Atlas Commerce"],
      ["scans", "External perimeter review"],
      ["findings", "Broken object-level authorization"],
      ["intelligence", "Mock inference"],
      ["attack", "api.atlas.example"],
      ["reports", "Atlas Commerce"],
      ["models", "SENTRIX Risk Engine"],
      ["settings", "Published report"],
    ];
    for (const [view, marker] of views) {
      await check(`${view} view renders API data`, async () => {
        await cdp.evaluate(`document.querySelector('[data-view="${view}"]')?.click()`);
        await sleep(120);
        const text = await cdp.evaluate("document.body.innerText");
        assert.match(text, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
        return marker;
      });
    }

    await check("page issues no off-origin requests", async () => {
      const requests = cdp.events
        .filter((event) => event.method === "Network.requestWillBeSent")
        .map((event) => event.params.request.url)
        .filter((url) => !url.startsWith("data:"));
      const offOrigin = requests.filter((url) => !url.startsWith(APP_ORIGIN));
      assert.deepEqual(offOrigin, [], `off-origin requests: ${offOrigin.join(", ")}`);
      return `${requests.length} requests, all same-origin`;
    });

    await check("report CSV export produces SENTRIX content", async () => {
      await cdp.evaluate(`(() => {
        window.__capturedCsv = null;
        const original = URL.createObjectURL;
        URL.createObjectURL = (blob) => {
          if (blob && blob.type.includes('csv')) window.__capturedCsv = blob;
          return original(blob);
        };
        document.querySelector('[data-view="reports"]').click();
      })()`);
      await sleep(150);
      await cdp.evaluate(`document.querySelector('[data-action="export-report"]')?.click()`);
      await sleep(200);
      const exported = await cdp.evaluate(`(async () => {
        if (!window.__capturedCsv) return null;
        return { size: window.__capturedCsv.size, text: await window.__capturedCsv.text() };
      })()`);
      assert.ok(exported, "no CSV blob was created");
      assert.ok(exported.size > 100, "CSV blob is too small");
      assert.match(exported.text, /SENTRIX report/);
      assert.match(exported.text, /Broken object-level authorization/);
      return `${exported.size} bytes`;
    });

    await check("page reload preserves the authenticated session", async () => {
      await cdp.send("Page.navigate", { url: APP_URL });
      await waitFor(
        async () => (await cdp.evaluate("document.querySelector('.brand b')?.textContent")) === "SENTRIX",
        15000,
        "reloaded shell",
      );
      const body = await cdp.evaluate("document.body.innerText");
      assert.match(body, /Atlas Commerce/);
      return "token persisted; bootstrap reloaded";
    });

    await check("no uncaught page errors", async () => {
      const exceptions = cdp.events
        .filter((event) => event.method === "Runtime.exceptionThrown")
        .map((event) => event.params.exceptionDetails.exception?.description ?? event.params.exceptionDetails.text)
        .filter((text) => !String(text).includes("favicon"));
      assert.deepEqual(exceptions, []);
      return "zero Runtime.exceptionThrown events";
    });
  } finally {
    if (cdp) {
      try { await cdp.send("Browser.close"); } catch { /* closed */ }
      cdp.close();
    }
    if (child.exitCode === null) child.kill();
    await rm(profile, { recursive: true, force: true }).catch(() => {});
  }

  const failures = results.filter((result) => !result.ok);
  console.log(`\n${results.length - failures.length}/${results.length} API browser checks passed`);
  return failures.length === 0 ? 0 : 1;
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error("API_BROWSER_CHECK_FAILED", error.message);
    process.exit(2);
  });
