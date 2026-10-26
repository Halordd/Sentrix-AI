import test from "node:test";
import assert from "node:assert/strict";

import { createApiRepository } from "../api.js";

const bootstrap = () => ({
  projects: [
    { id: "project-atlas", name: "Atlas Commerce", owner: "Maya Chen", status: "Active", scope: "https://atlas.example/*", createdAt: "2026-10-01" },
  ],
  targets: [
    { id: "target-atlas-api", projectId: "project-atlas", name: "atlas-api", type: "API", authorized: true, scope: "https://api.atlas.example/*", status: "Monitored" },
  ],
  scans: [],
  findings: [
    {
      id: "finding-1",
      scanId: "scan-1",
      projectId: "project-atlas",
      targetId: "target-atlas-api",
      title: "Broken object-level authorization",
      severity: "High",
      status: "In Progress",
      evidence: "Evidence, with a comma and \"quotes\".",
      createdAt: "2026-10-26T00:00:00Z",
      notes: "",
    },
  ],
  analyses: [],
  remediations: [
    {
      id: "task-1",
      findingId: "finding-1",
      assignee: "Maya Chen",
      dueDate: "2026-10-30",
      status: "In Progress",
      notes: "Fix it",
      verification: null,
    },
  ],
  reports: [
    { id: "report-1", projectId: "project-atlas", scanId: null, title: "Atlas report", status: "Draft", createdAt: "2026-10-26" },
  ],
  audit: [],
  models: [],
  datasets: [],
});

function mockFetch(handler) {
  globalThis.localStorage = {
    getItem: () => "test-token",
    setItem: () => {},
    removeItem: () => {},
  };
  globalThis.fetch = async (url, options) => handler(url, options);
  return {
    json: (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body }),
  };
}

test("verification updates the linked finding after one POST", async () => {
  let verifyCalls = 0;
  const mocks = mockFetch((url, options) => {
    if (url === "/api/v1/bootstrap") return mocks.json(200, bootstrap());
    if (url === "/api/v1/remediations/task-1/verify") {
      verifyCalls += 1;
      assert.equal(options.method, "POST");
      return mocks.json(200, {
        id: "task-1",
        findingId: "finding-1",
        status: "Completed",
        verification: "VERIFIED",
        findingStatus: "Resolved",
      });
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  const repo = await createApiRepository();
  repo.verifyRemediation("task-1", "Verified");
  await new Promise((resolve) => setTimeout(resolve, 20));
  const snapshot = repo.snapshot();
  assert.equal(verifyCalls, 1);
  assert.equal(snapshot.remediations[0].status, "Completed");
  assert.equal(snapshot.findings[0].status, "Resolved");
});

test("CSV export matches the domain format from API data", async () => {
  const mocks = mockFetch((url) => {
    if (url === "/api/v1/bootstrap") return mocks.json(200, bootstrap());
    throw new Error(`unexpected fetch ${url}`);
  });
  const repo = await createApiRepository();
  const csv = repo.exportReportCsv("report-1");
  assert.equal(
    csv,
    [
      '"SENTRIX report","Atlas report"',
      '"Project","Atlas Commerce"',
      '"Scope","https://atlas.example/*"',
      '',
      '"Severity","Status","Finding","Target","Evidence"',
      '"High","In Progress","Broken object-level authorization","atlas-api","Evidence, with a comma and ""quotes""."',
    ].join("\n"),
  );
});
