/**
 * SENTRIX prototype domain module.
 *
 * This is an in-memory adapter, deliberately kept behind one interface so it
 * can be replaced by an authenticated API adapter without changing views.
 * It does not contact targets or execute security tooling.
 */
const now = () => new Date().toISOString();
const uid = (prefix) => `${prefix}-${Math.random().toString(36).slice(2, 8)}`;

const initialData = () => ({
  projects: [
    { id: "project-atlas", name: "Atlas Commerce", owner: "Maya Chen", status: "Active", scope: "Public web application and authenticated API", createdAt: "2026-10-12" },
    { id: "project-helix", name: "Helix Payments", owner: "Jon Bell", status: "Active", scope: "Payment API and cloud configuration", createdAt: "2026-10-09" },
    { id: "project-northstar", name: "Northstar API", owner: "Priya Nair", status: "Active", scope: "Public API endpoints", createdAt: "2026-10-02" },
  ],
  targets: [
    { id: "target-atlas-api", projectId: "project-atlas", name: "api.atlas.example", type: "API", authorized: true, scope: "https://api.atlas.example/v2/*", status: "Monitored" },
    { id: "target-atlas-web", projectId: "project-atlas", name: "app.atlas.example", type: "Web", authorized: true, scope: "https://app.atlas.example/*", status: "Monitored" },
    { id: "target-helix-api", projectId: "project-helix", name: "payments.helix.example", type: "API", authorized: true, scope: "https://payments.helix.example/*", status: "Monitored" },
    { id: "target-northstar", projectId: "project-northstar", name: "api.northstar.example", type: "API", authorized: false, scope: "", status: "Blocked" },
  ],
  scans: [
    { id: "scan-atlas", projectId: "project-atlas", targetId: "target-atlas-api", name: "External perimeter review", profile: "External attack surface", status: "Completed", progress: 100, simulated: true, createdAt: "2026-10-18T02:20:00.000Z", completedAt: "2026-10-18T02:43:00.000Z" },
    { id: "scan-helix", projectId: "project-helix", targetId: "target-helix-api", name: "API authorization audit", profile: "API authorization", status: "Completed", progress: 100, simulated: true, createdAt: "2026-10-18T00:12:00.000Z", completedAt: "2026-10-18T00:35:00.000Z" },
    { id: "scan-atlas-running", projectId: "project-atlas", targetId: "target-atlas-web", name: "Web configuration review", profile: "External attack surface", status: "Running", progress: 78, simulated: true, createdAt: "2026-10-18T03:44:00.000Z" },
  ],
  findings: [
    { id: "finding-bola", scanId: "scan-atlas", projectId: "project-atlas", targetId: "target-atlas-api", title: "Broken object-level authorization", severity: "Critical", status: "Confirmed", evidence: "Illustrative evidence: simulated response showed a tenant mismatch during an authorized demo replay.", createdAt: "2026-10-18T02:43:00.000Z", notes: "Validate ownership checks before remediation." },
    { id: "finding-bucket", scanId: "scan-helix", projectId: "project-helix", targetId: "target-helix-api", title: "Public storage policy", severity: "High", status: "New", evidence: "Illustrative configuration observation from simulated scan output.", createdAt: "2026-10-18T00:35:00.000Z", notes: "" },
    { id: "finding-debug", scanId: "scan-atlas", projectId: "project-atlas", targetId: "target-atlas-web", title: "Exposed debug endpoint", severity: "Medium", status: "Accepted Risk", evidence: "Illustrative endpoint observation from simulated scan output.", createdAt: "2026-10-17T18:06:00.000Z", notes: "Risk owner accepted until next release." },
  ],
  analyses: [
    { id: "analysis-bola", findingId: "finding-bola", model: "SENTRIX Risk Engine", version: "4.8.2", status: "Completed", confidence: 91, summary: "High-confidence authorization defect. Business impact is elevated because the affected asset processes customer orders.", limitations: "Mock inference for prototype demonstration only; not a scanner or trained-model result.", createdAt: "2026-10-18T02:45:00.000Z", simulated: true },
  ],
  remediations: [
    { id: "task-bola", findingId: "finding-bola", assignee: "Maya Chen", dueDate: "2026-10-24", status: "In Progress", notes: "Implement object ownership authorization on order reads.", verification: null },
  ],
  reports: [
    { id: "report-atlas", projectId: "project-atlas", scanId: "scan-atlas", title: "Atlas Commerce — Security assessment", status: "Published", createdAt: "2026-10-18T03:00:00.000Z" },
  ],
  audit: [
    { id: "audit-1", at: "2026-10-18T03:00:00.000Z", actor: "Maya Chen", action: "Published report", resource: "Atlas Commerce security assessment", outcome: "Success" },
    { id: "audit-2", at: "2026-10-18T02:45:00.000Z", actor: "SENTRIX demo service", action: "Completed AI analysis", resource: "Broken object-level authorization", outcome: "Simulated" },
  ],
  models: [
    { id: "model-risk", name: "SENTRIX Risk Engine", version: "4.8.2", status: "Production", precision: "Sample 0.91", recall: "Sample 0.88", f1: "Sample 0.89", inference: "Sample 420 ms" },
    { id: "model-evidence", name: "Evidence Summarizer", version: "2.4.1", status: "Production", precision: "Sample 0.86", recall: "Sample 0.84", f1: "Sample 0.85", inference: "Sample 280 ms" },
  ],
  datasets: [{ id: "dataset-demo", name: "Demo vulnerability evaluation set", version: "2026.09", samples: 1280, provenance: "Sample data — demo only", labels: "Critical 12% · High 28% · Medium 40% · Low 20%" }],
});

export function createSentrixRepository(seed = initialData()) {
  const data = structuredClone(seed);
  const event = (action, resource, outcome = "Success") => data.audit.unshift({ id: uid("audit"), at: now(), actor: "Maya Chen", action, resource, outcome });
  const byId = (collection, id) => data[collection].find((item) => item.id === id);
  const requireValue = (value, message) => { if (!String(value ?? "").trim()) throw new Error(message); };

  return {
    snapshot: () => structuredClone(data),
    createProject(input) {
      requireValue(input.name, "Project name is required.");
      if (data.projects.some((p) => p.name.toLowerCase() === input.name.trim().toLowerCase())) throw new Error("A project with this name already exists.");
      const project = { id: uid("project"), name: input.name.trim(), owner: input.owner?.trim() || "Maya Chen", status: "Active", scope: input.scope?.trim() || "Not configured", createdAt: now().slice(0, 10) };
      data.projects.unshift(project); event("Created project", project.name); return structuredClone(project);
    },
    archiveProject(projectId) {
      const project = byId("projects", projectId); if (!project) throw new Error("Project not found.");
      project.status = "Archived"; event("Archived project", project.name); return structuredClone(project);
    },
    createTarget(input) {
      requireValue(input.name, "Target hostname or URL is required."); requireValue(input.projectId, "Select a project."); requireValue(input.scope, "Authorized scope is required.");
      if (!input.authorizationConfirmed) throw new Error("Explicit authorization confirmation is required before a target can be used.");
      const project = byId("projects", input.projectId); if (!project || project.status === "Archived") throw new Error("Select an active project.");
      const target = { id: uid("target"), projectId: input.projectId, name: input.name.trim(), type: input.type || "Web", authorized: true, scope: input.scope.trim(), status: "Monitored" };
      data.targets.unshift(target); event("Configured authorized target", target.name); return structuredClone(target);
    },
    createScan(input) {
      requireValue(input.name, "Scan name is required."); const target = byId("targets", input.targetId);
      if (!target) throw new Error("Select a target."); if (!target.authorized || !target.scope) throw new Error("This target is blocked: configure and explicitly authorize its scope first.");
      const project = byId("projects", target.projectId); if (!project || project.status === "Archived") throw new Error("Select an active project.");
      const scan = { id: uid("scan"), projectId: target.projectId, targetId: target.id, name: input.name.trim(), profile: input.profile || "External attack surface", status: "Queued", progress: 0, simulated: true, createdAt: now() };
      data.scans.unshift(scan); event("Queued simulated scan", scan.name, "Simulated"); return structuredClone(scan);
    },
    runSimulatedScan(scanId) {
      const scan = byId("scans", scanId); if (!scan) throw new Error("Scan not found.");
      if (!["Queued", "Failed"].includes(scan.status)) throw new Error("Only queued or failed scans can be started.");
      scan.status = "Completed"; scan.progress = 100; scan.completedAt = now(); event("Completed simulated scan", scan.name, "Simulated");
      const exists = data.findings.some((f) => f.scanId === scan.id); if (!exists) {
        const finding = { id: uid("finding"), scanId: scan.id, projectId: scan.projectId, targetId: scan.targetId, title: "Demo configuration exposure", severity: "Low", status: "New", evidence: "Illustrative evidence generated by the deterministic demo scan. No external target was contacted.", createdAt: now(), notes: "Review with engagement owner." };
        data.findings.unshift(finding); event("Recorded demo finding", finding.title, "Simulated");
      }
      return structuredClone(scan);
    },
    cancelScan(scanId) { const scan = byId("scans", scanId); if (!scan || !["Queued", "Running"].includes(scan.status)) throw new Error("Only active scans can be cancelled."); scan.status = "Cancelled"; event("Cancelled scan", scan.name); return structuredClone(scan); },
    updateFindingStatus(findingId, status) { const finding = byId("findings", findingId); if (!finding) throw new Error("Finding not found."); finding.status = status; event("Updated finding status", finding.title); return structuredClone(finding); },
    createAnalysis(findingId) {
      const finding = byId("findings", findingId); if (!finding) throw new Error("Finding not found.");
      const existing = data.analyses.find((a) => a.findingId === findingId); if (existing) return structuredClone(existing);
      const analysis = { id: uid("analysis"), findingId, model: "SENTRIX Risk Engine", version: "4.8.2", status: "Completed", confidence: finding.severity === "Critical" ? 91 : 76, summary: `Mock risk assessment for ${finding.title}. Analyst review is required before action.`, limitations: "Mock inference for prototype demonstration only; no model was invoked.", createdAt: now(), simulated: true };
      data.analyses.unshift(analysis); event("Completed AI analysis", finding.title, "Simulated"); return structuredClone(analysis);
    },
    createRemediation(input) { const finding = byId("findings", input.findingId); if (!finding) throw new Error("Finding not found."); requireValue(input.assignee, "Assignee is required."); const task = { id: uid("task"), findingId: finding.id, assignee: input.assignee.trim(), dueDate: input.dueDate || "", status: "In Progress", notes: input.notes?.trim() || "", verification: null }; data.remediations.unshift(task); finding.status = "In Progress"; event("Created remediation task", finding.title); return structuredClone(task); },
    verifyRemediation(taskId, outcome) { const task = byId("remediations", taskId); if (!task) throw new Error("Remediation task not found."); const finding = byId("findings", task.findingId); task.verification = outcome; task.status = outcome === "Verified" ? "Completed" : "Reopened"; finding.status = outcome === "Verified" ? "Resolved" : "Reopened"; event("Recorded verification outcome", finding.title, outcome === "Verified" ? "Simulated" : "Success"); return structuredClone(task); },
    createReport(input) { requireValue(input.projectId, "Select a project."); const project = byId("projects", input.projectId); if (!project) throw new Error("Project not found."); const report = { id: uid("report"), projectId: project.id, scanId: input.scanId || null, title: input.title?.trim() || `${project.name} — Security assessment`, status: "Draft", createdAt: now() }; data.reports.unshift(report); event("Generated report draft", report.title); return structuredClone(report); },
    publishReport(reportId) { const report = byId("reports", reportId); if (!report) throw new Error("Report not found."); report.status = "Published"; event("Published report", report.title); return structuredClone(report); },
    exportReportCsv(reportId) {
      const report = byId("reports", reportId); if (!report) throw new Error("Report not found."); const project = byId("projects", report.projectId); const findings = data.findings.filter((f) => f.projectId === project.id);
      const clean = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
      const rows = [["SENTRIX report", report.title], ["Project", project.name], ["Scope", project.scope], [], ["Severity", "Status", "Finding", "Target", "Evidence"]];
      findings.forEach((f) => rows.push([f.severity, f.status, f.title, byId("targets", f.targetId)?.name || "", f.evidence]));
      event("Exported report CSV", report.title); return rows.map((row) => row.map(clean).join(",")).join("\n");
    },
  };
}

