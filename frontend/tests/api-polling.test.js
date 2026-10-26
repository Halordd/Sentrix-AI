import test from "node:test";
import assert from "node:assert/strict";

import { createApiRepository } from "../api.js";

test("scan polling refreshes completed run and finding", async () => {
  globalThis.localStorage = {
    getItem: () => "test-token",
    setItem: () => {},
    removeItem: () => {},
  };
  let scans = 0;
  globalThis.fetch = async (url) => {
    if (url === "/api/v1/bootstrap") {
      return {
        status: 200,
        ok: true,
        json: async () => ({
          projects: [],
          targets: [],
          scans: [
            {
              id: "scan-1",
              projectId: "project-1",
              targetId: "target-1",
              name: "Polling scan",
              profile: "API authorization",
              status: "Queued",
              progress: 0,
              simulated: true,
              createdAt: "2026-10-26T00:00:00Z",
              completedAt: null,
            },
          ],
          findings: [],
          analyses: [],
          remediations: [],
          reports: [],
          audit: [],
          models: [],
          datasets: [],
        }),
      };
    }
    if (url === "/api/v1/scans/scan-1") {
      scans += 1;
      return {
        status: 200,
        ok: true,
        json: async () => ({
          status: "Completed",
          progress: 100,
          completedAt: "2026-10-26T00:00:02Z",
          run: { status: "SUCCEEDED", error: null },
          findings: [
            {
              id: "finding-1",
              scanId: "scan-1",
              projectId: "project-1",
              targetId: "target-1",
              title: "Polled finding",
              severity: "High",
              status: "New",
              evidence: "observed",
              createdAt: "2026-10-26T00:00:02Z",
              notes: "",
            },
          ],
        }),
      };
    }
    throw new Error(`unexpected fetch ${url}`);
  };

  const repo = await createApiRepository();
  repo.runSimulatedScan("scan-1");
  await new Promise((resolve) => setTimeout(resolve, 1_200));

  const snapshot = repo.snapshot();
  assert.equal(scans, 1);
  assert.equal(snapshot.scans[0].status, "Completed");
  assert.equal(snapshot.scans[0].progress, 100);
  assert.equal(snapshot.findings.length, 1);
  assert.equal(snapshot.findings[0].id, "finding-1");
});
