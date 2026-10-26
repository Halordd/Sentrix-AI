/**
 * Browser verification for the SENTRIX prototype.
 *
 * Launches a headless Chromium-based browser (Microsoft Edge or Chrome) with the
 * DevTools protocol, drives the real UI, and reports pass/fail per workflow.
 * Uses only Node built-ins: no Playwright, Puppeteer or Selenium.
 *
 *   npm run dev          # in one terminal
 *   npm run verify:browser
 *
 * Environment overrides: APP_URL, CDP_PORT, EDGE_PATH, BROWSER_PATH.
 * Exits 0 when every check passes, 1 when a check fails, 2 when no browser is
 * available or it cannot be reached.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE_URL = process.env.APP_URL ?? "http://127.0.0.1:3000/";
const APP_URL =
  process.env.REPO_MODE === "api"
    ? BASE_URL
    : BASE_URL + (BASE_URL.includes("?") ? "&" : "?") + "repo=memory";
const CDP_PORT = Number(process.env.CDP_PORT ?? 9401);
const APP_ORIGIN = new URL(APP_URL).origin;
const BROWSER_CANDIDATES = [
  process.env.EDGE_PATH,
  process.env.BROWSER_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/microsoft-edge",
  "/usr/bin/microsoft-edge-stable",
  "/usr/bin/google-chrome",
].filter(Boolean);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const PAGE_HELPERS = `
  window.__text = (selector) => document.querySelector(selector)?.textContent?.trim() ?? null;
  window.__toast = () => document.querySelector('.toast')?.textContent?.trim() ?? null;
  window.__rows = () => [...document.querySelectorAll('tbody tr')].map((row) => row.textContent.trim());
  window.__click = (selector) => {
    const element = document.querySelector(selector);
    if (!element) throw new Error('missing element: ' + selector);
    element.click();
  };
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
  // Dispatch submit directly to exercise the app's domain validation instead of
  // the browser's native required-field check.
  window.__submitRaw = (selector) => {
    const form = document.querySelector(selector);
    if (!form) throw new Error('missing form: ' + selector);
    form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  };
  'helpers-ready';
`;

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 0;
    this.pending = new Map();
    this.events = [];
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message));
        else resolve(message.result);
        return;
      }
      if (message.method) this.events.push(message);
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
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const response = await this.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (response.exceptionDetails) {
      throw new Error(response.exceptionDetails.exception?.description ?? response.exceptionDetails.text);
    }
    return response.result.value;
  }

  close() {
    try { this.socket.close(); } catch { /* already closed */ }
  }
}

async function waitFor(predicate, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await sleep(100);
  }
  throw new Error(`timed out waiting for ${label}`);
}

async function launchBrowser(profileDirectory) {
  const executable = BROWSER_CANDIDATES.find((candidate) => existsSync(candidate));
  if (!executable) return null;
  const child = spawn(executable, [
    "--headless=new",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--no-first-run",
    "--no-default-browser-check",
    "--user-data-dir=" + profileDirectory,
    "--remote-debugging-port=" + CDP_PORT,
    "about:blank",
  ], { stdio: "ignore" });
  return { executable, child };
}

async function stopBrowser(state, cdp) {
  if (cdp) {
    try { await cdp.send("Browser.close"); } catch { /* already gone */ }
    cdp.close();
  }
  if (state?.child && state.child.exitCode === null) {
    state.child.kill();
  }
  if (state?.profile) {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      try { await rm(state.profile, { recursive: true, force: true }); return; } catch { await sleep(200); }
    }
  }
}

async function run() {
  const probe = await fetch(`${APP_ORIGIN}/`).catch(() => null);
  if (!probe?.ok) throw new Error(`application not reachable at ${APP_ORIGIN}; start it with "npm run dev"`);

  const profile = await mkdtemp(join(tmpdir(), "sentrix-browser-"));
  const state = await launchBrowser(profile);
  if (!state) {
    await rm(profile, { recursive: true, force: true });
    console.log("SKIPPED: no Chromium-based browser (Edge/Chrome) found on this machine");
    return 2;
  }
  state.profile = profile;

  let cdp = null;
  const results = [];
  const check = async (name, body) => {
    try {
      const detail = await body();
      results.push({ name, ok: true, detail });
    } catch (error) {
      results.push({ name, ok: false, detail: error.message });
    }
  };

  try {
    await waitFor(async () => {
      if (state.child.exitCode !== null) {
        throw new Error(`browser exited before DevTools was ready (code ${state.child.exitCode}); Chromium cannot start inside a sandbox that blocks its IPC — run this check with unconfined execution`);
      }
      const response = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`).catch(() => null);
      return response?.ok === true;
    }, 20000, "devtools endpoint");

    const created = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(APP_URL)}`, { method: "PUT" });
    if (!created.ok) throw new Error(`could not open a browser target: ${created.status}`);
    const target = await created.json();
    cdp = await Cdp.connect(target.webSocketDebuggerUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Log.enable");
    await cdp.send("Network.enable");
    await cdp.send("Page.navigate", { url: APP_URL });
    await waitFor(async () => (await cdp.evaluate("document.readyState")) === "complete", 15000, "page load");
    await waitFor(async () => (await cdp.evaluate("document.querySelector('.brand b')?.textContent")) === "SENTRIX", 10000, "app render");
    await cdp.evaluate(PAGE_HELPERS);

    await check("page renders the SENTRIX shell", async () => {
      const view = await cdp.evaluate(`({
        brand: __text('.brand b'),
        title: __text('.page-heading h1'),
        metrics: document.querySelectorAll('.metrics .metric-card').length,
        banner: __text('.demo-banner'),
      })`);
      assert.equal(view.brand, "SENTRIX");
      assert.equal(view.title, "Overview");
      assert.equal(view.metrics, 4);
      assert.match(view.banner, /DEMO MODE/);
      return "overview + 4 metrics + demo banner";
    });

    await check("page issues no off-origin network requests", async () => {
      const requests = cdp.events
        .filter((event) => event.method === "Network.requestWillBeSent")
        .map((event) => event.params.request.url)
        .filter((url) => !url.startsWith("data:"));
      const offOrigin = requests.filter((url) => !url.startsWith(APP_ORIGIN));
      assert.deepEqual(offOrigin, [], `off-origin requests: ${offOrigin.join(", ")}`);
      return `${requests.length} requests, all same-origin`;
    });

    await check("recovery artifacts are denied to the page", async () => {
      const statuses = await cdp.evaluate(`Promise.all([
        '/.dsh-acl-recovery/',
        '/.dsh-acl-recovery/acl-backup-8f29de683dcf436fa326714234ef161e.json',
        '/%2edsh-acl-recovery/x',
        '/..%2fREADME.md',
      ].map(async (path) => (await fetch(path)).status))`);
      assert.ok(statuses.every((status) => status === 400 || status === 403), `unexpected statuses: ${statuses.join(", ")}`);
      return "403 for raw, encoded and traversal forms";
    });

    await check("project creation", async () => {
      await cdp.evaluate(`__click('[data-view="projects"]')`);
      await sleep(30);
      await cdp.evaluate(`__click('[data-action="new-project"]')`);
      await cdp.evaluate(`
        __setValue('#project-form input[name="name"]', 'Browser Verify Project');
        __setValue('#project-form input[name="owner"]', 'Maya Chen');
        __setValue('#project-form textarea[name="scope"]', 'https://verify.example/*');
        __submit('#project-form');
      `);
      await sleep(50);
      const after = await cdp.evaluate(`({ toast: __toast(), title: __text('.page-heading h1'), rows: __rows().join(' | ') })`);
      assert.match(after.toast, /Project created/);
      assert.match(after.title, /Projects/);
      assert.match(after.rows, /Browser Verify Project/);
      return "created, toast shown, row listed";
    });

    await check("target creation is refused without authorization", async () => {
      await cdp.evaluate(`__click('[data-action="new-target"]')`);
      await cdp.evaluate(`
        __setValue('#target-form input[name="name"]', 'verify.example');
        __setValue('#target-form input[name="scope"]', 'https://verify.example/*');
        __submitRaw('#target-form');
      `);
      await sleep(50);
      const after = await cdp.evaluate(`({ toast: __toast(), modal: Boolean(document.querySelector('.modal')) })`);
      assert.match(after.toast, /Explicit authorization confirmation is required/);
      assert.equal(after.modal, true, "modal should stay open for correction");
      return "domain refused the unchecked authorization";
    });

    await check("authorized target is recorded", async () => {
      await cdp.evaluate(`
        __setValue('#target-form input[name="name"]', 'verify.example');
        __setValue('#target-form input[name="scope"]', 'https://verify.example/*');
        document.querySelector('#target-form input[name="authorizationConfirmed"]').checked = true;
        __submit('#target-form');
      `);
      await sleep(50);
      const after = await cdp.evaluate(`({ toast: __toast(), title: __text('.page-heading h1'), rows: __rows().join(' | ') })`);
      assert.match(after.toast, /Authorized target recorded/);
      assert.match(after.title, /Attack Surface/);
      assert.match(after.rows, /verify\.example/);
      return "recorded and listed in the asset inventory";
    });

    await check("simulated scan runs to completion", async () => {
      await cdp.evaluate(`__click('[data-view="scans"]')`);
      await sleep(30);
      await cdp.evaluate(`__click('[data-action="new-scan"]')`);
      await cdp.evaluate(`
        __setValue('#scan-form input[name="name"]', 'Browser Verify Scan');
        __submit('#scan-form');
      `);
      await sleep(50);
      const queued = await cdp.evaluate(`({ toast: __toast(), rows: __rows().join(' | ') })`);
      assert.match(queued.toast, /Simulated scan queued/);
      assert.match(queued.rows, /Browser Verify Scan/);
      await cdp.evaluate(`(() => {
        const row = [...document.querySelectorAll('tbody tr')].find((item) => item.textContent.includes('Browser Verify Scan'));
        row.querySelector('[data-action="run-scan"]').click();
      })()`);
      await sleep(50);
      const ran = await cdp.evaluate(`({ toast: __toast(), rows: __rows().join(' | ') })`);
      assert.match(ran.toast, /Scan queued|Scan completed|waiting/);
      assert.match(ran.rows, /Completed/);
      return "queued, run demo, status Completed";
    });

    await check("simulated scan produced a finding", async () => {
      await cdp.evaluate(`__click('[data-view="findings"]')`);
      await sleep(30);
      const rows = await cdp.evaluate(`__rows().join(' | ')`);
      assert.match(rows, /Demo configuration exposure/);
      return "finding linked to the scan is listed";
    });

    await check("finding filter survives a re-render", async () => {
      await cdp.evaluate(`(() => {
        const select = document.querySelector('#finding-filter');
        select.value = 'Critical';
        select.dispatchEvent(new Event('change', { bubbles: true }));
      })()`);
      await sleep(30);
      const filtered = await cdp.evaluate(`({
        value: document.querySelector('#finding-filter')?.value,
        badges: [...document.querySelectorAll('tbody tr td:nth-child(2) .badge')].map((badge) => badge.textContent.trim()),
      })`);
      assert.equal(filtered.value, "Critical");
      assert.ok(filtered.badges.length > 0, "filtered table should not be empty");
      assert.ok(filtered.badges.every((badge) => badge === "Critical"));
      await cdp.evaluate(`(() => {
        const select = document.querySelector('#finding-filter');
        select.value = 'All';
        select.dispatchEvent(new Event('change', { bubbles: true }));
      })()`);
      return "select keeps Critical after render; only Critical rows shown";
    });

    await check("remediation verification resolves the finding", async () => {
      await cdp.evaluate(`(() => {
        const row = [...document.querySelectorAll('tbody tr')].find((item) => item.textContent.includes('Public storage policy'));
        row.querySelector('[data-open="finding"]').click();
      })()`);
      await sleep(30);
      await cdp.evaluate(`__click('[data-action="new-remediation"]')`);
      await sleep(30);
      const created = await cdp.evaluate(`({ toast: __toast(), hasVerify: Boolean(document.querySelector('.modal [data-action="verify"]')) })`);
      assert.match(created.toast, /Remediation task created/);
      assert.equal(created.hasVerify, true);
      await cdp.evaluate(`__click('[data-action="verify"]')`);
      await sleep(30);
      const verified = await cdp.evaluate(`({ toast: __toast(), modal: __text('.modal') })`);
      assert.match(verified.toast, /Simulated verification recorded/);
      assert.match(verified.modal, /Resolved/);
      assert.match(verified.modal, /Verified/);
      await cdp.evaluate(`document.querySelector('.modal [data-action="close"]').click()`);
      return "task created, verification recorded, finding Resolved";
    });

    await check("report export produces CSV content", async () => {
      await cdp.evaluate(`(() => {
        window.__capturedCsv = null;
        const original = URL.createObjectURL;
        URL.createObjectURL = (blob) => {
          if (blob && blob.type.includes('csv')) window.__capturedCsv = blob;
          return original(blob);
        };
      })()`);
      await cdp.evaluate(`__click('[data-view="reports"]')`);
      await sleep(30);
      await cdp.evaluate(`__click('[data-action="export-report"]')`);
      await sleep(50);
      const exported = await cdp.evaluate(`(async () => {
        if (!window.__capturedCsv) return null;
        return { size: window.__capturedCsv.size, text: await window.__capturedCsv.text() };
      })()`);
      assert.ok(exported, "no CSV blob was created");
      assert.ok(exported.size > 100, "CSV blob is suspiciously small");
      assert.match(exported.text, /SENTRIX report/);
      assert.match(exported.text, /Broken object-level authorization/);
      const toast = await cdp.evaluate(`__toast()`);
      assert.match(toast, /CSV report export downloaded/);
      return `${exported.size} bytes, SENTRIX header + finding rows, toast shown`;
    });

    await check("archived projects cannot be scanned", async () => {
      await cdp.evaluate(`__click('[data-view="projects"]')`);
      await sleep(30);
      await cdp.evaluate(`(() => {
        const row = [...document.querySelectorAll('tbody tr')].find((item) => item.textContent.includes('Atlas Commerce'));
        row.querySelector('[data-open="project"]').click();
      })()`);
      await sleep(30);
      await cdp.evaluate(`__click('[data-action="archive-project"]')`);
      await sleep(30);
      const archived = await cdp.evaluate(`({ toast: __toast(), rows: __rows().join(' | ') })`);
      assert.match(archived.toast, /Project archived/);
      assert.match(archived.rows, /Archived/);
      await cdp.evaluate(`__click('[data-view="scans"]')`);
      await sleep(30);
      await cdp.evaluate(`__click('[data-action="new-scan"]')`);
      await sleep(30);
      const options = await cdp.evaluate(`[...document.querySelectorAll('#scan-form option')].map((option) => option.textContent.trim())`);
      assert.ok(options.length > 0, "scan form should still list active-project targets");
      assert.ok(!options.some((option) => option.includes("api.atlas.example")), "archived project's target must not be offered");
      await cdp.evaluate(`document.querySelector('.modal [data-action="close"]').click()`);
      return "archive shown; archived target absent from scan form";
    });

    await check("no uncaught page errors", async () => {
      const exceptions = cdp.events
        .filter((event) => event.method === "Runtime.exceptionThrown")
        .map((event) => event.params.exceptionDetails.exception?.description ?? event.params.exceptionDetails.text);
      assert.deepEqual(exceptions, []);
      return "zero Runtime.exceptionThrown events";
    });

    const failures = results.filter((result) => !result.ok);
    for (const result of results) {
      console.log(`${result.ok ? "PASS" : "FAIL"}  ${result.name}${result.detail ? ` — ${result.detail}` : ""}`);
    }
    console.log(`\n${results.length - failures.length}/${results.length} browser checks passed`);
    return failures.length === 0 ? 0 : 1;
  } finally {
    await stopBrowser(state, cdp);
  }
}

const exitCode = await run().catch((error) => {
  console.error(`BROWSER_CHECK_ERROR ${error.message}`);
  return 2;
});
process.exit(exitCode);
