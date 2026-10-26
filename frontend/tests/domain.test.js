import test from "node:test";
import assert from "node:assert/strict";
import { createSentrixRepository } from "../domain.js";

test("a target must have configured scope and explicit authorization", () => {
  const repo = createSentrixRepository();
  assert.throws(() => repo.createTarget({ projectId: "project-atlas", name: "new.atlas.example", scope: "https://new.atlas.example/*" }), /Explicit authorization/);
  const target = repo.createTarget({ projectId: "project-atlas", name: "new.atlas.example", scope: "https://new.atlas.example/*", authorizationConfirmed: true });
  assert.equal(target.authorized, true);
});

test("a simulated scan creates a related finding without contacting a target", () => {
  const repo = createSentrixRepository();
  const scan = repo.createScan({ name: "Demo scan", targetId: "target-atlas-api" });
  repo.runSimulatedScan(scan.id);
  const finding = repo.snapshot().findings.find((item) => item.scanId === scan.id);
  assert.equal(finding.projectId, "project-atlas");
  assert.equal(finding.targetId, "target-atlas-api");
  assert.match(finding.evidence, /No external target was contacted/);
});

test("verification, not task completion alone, resolves a finding", () => {
  const repo = createSentrixRepository();
  const task = repo.createRemediation({ findingId: "finding-bucket", assignee: "Maya Chen" });
  assert.equal(repo.snapshot().findings.find((f) => f.id === "finding-bucket").status, "In Progress");
  repo.verifyRemediation(task.id, "Verified");
  assert.equal(repo.snapshot().findings.find((f) => f.id === "finding-bucket").status, "Resolved");
});

test("a report export is generated from project findings", () => {
  const repo = createSentrixRepository();
  const report = repo.createReport({ projectId: "project-atlas", title: "Atlas demo report" });
  const csv = repo.exportReportCsv(report.id);
  assert.match(csv, /Atlas demo report/);
  assert.match(csv, /Broken object-level authorization/);
});

test("a scan cannot be queued against an archived project", () => {
  const repo = createSentrixRepository();
  repo.archiveProject("project-atlas");
  assert.throws(() => repo.createScan({ name: "Late scan", targetId: "target-atlas-api" }), /active project/);
});
