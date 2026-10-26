import test from "node:test";
import assert from "node:assert/strict";

import { createRepository } from "../repository.js";

test("repository factory selects the in-memory adapter explicitly", async () => {
  const repo = await createRepository({ mode: "memory" });
  const snapshot = repo.snapshot();
  assert.equal(snapshot.projects.length, 3);
  assert.equal(snapshot.findings.length, 3);
  assert.equal(typeof repo.createProject, "function");
});

test("repository factory rejects API auth failures instead of hiding them", async () => {
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  };
  await assert.rejects(() => createRepository({ mode: "api" }), /AUTH_REQUIRED/);
});
