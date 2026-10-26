import test from "node:test";
import assert from "node:assert/strict";

// Minimal DOM stand-in: app.js only needs a node to render into plus empty
// query results, because every listener it binds targets generated markup.
const appElement = { innerHTML: "" };
globalThis.document = {
  querySelector: (selector) => (selector === "#app" ? appElement : null),
  querySelectorAll: () => [],
  addEventListener: () => {},
};
globalThis.localStorage = {
  getItem: () => "test-token",
  setItem: () => {},
  removeItem: () => {},
};
globalThis.window = {
  location: { replace: () => {} },
};
globalThis.fetch = async () => {
  throw new Error("offline in unit test");
};

const { action, render, state } = await import("../app.js");

const views = ["overview", "projects", "scans", "findings", "intelligence", "attack", "reports", "models", "settings"];
const reset = (view = "overview") => {
  state.view = view;
  state.modal = null;
  state.selectedId = null;
  state.search = "";
  state.statusFilter = "All";
  state.toast = null;
};

test("every view renders the application shell", () => {
  for (const view of views) {
    reset(view);
    render();
    assert.match(appElement.innerHTML, /class="shell"/, `view ${view} failed to render`);
  }
});

test("the project status filter stays selected after a re-render", () => {
  reset("projects");
  state.statusFilter = "Active";
  render();
  assert.match(appElement.innerHTML, /<option selected>Active<\/option>/);
  assert.doesNotMatch(appElement.innerHTML, /<option selected>All<\/option>/);
});

test("the finding filter stays selected after a re-render", () => {
  reset("findings");
  state.statusFilter = "Critical";
  render();
  assert.match(appElement.innerHTML, /<option selected>Critical<\/option>/);
});

test("global search clears a filter left over from another view", () => {
  reset("findings");
  state.search = "bola";
  state.statusFilter = "Critical";
  action("focus-search");
  assert.equal(state.view, "projects");
  assert.equal(state.search, "");
  assert.equal(state.statusFilter, "All");
});

test("every modal type renders as a dialog", () => {
  const cases = [
    ["project", null],
    ["target", null],
    ["scan", null],
    ["report", null],
    ["project-detail", "project-atlas"],
    ["scan-detail", "scan-atlas"],
    ["finding-detail", "finding-bola"],
  ];
  for (const [modal, selectedId] of cases) {
    reset("overview");
    state.modal = modal;
    state.selectedId = selectedId;
    render();
    assert.match(appElement.innerHTML, /role="dialog"/, `modal ${modal} failed to render`);
  }
});
