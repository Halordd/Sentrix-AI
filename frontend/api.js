const readOnly = () => {
  throw new Error("Read-only demo: this action is not implemented yet.");
};

const token = () => localStorage.getItem("sentrix_token");

const authHeaders = () => {
  const value = token();
  return value ? { Authorization: `Bearer ${value}` } : {};
};

const unauthorized = () => {
  localStorage.removeItem("sentrix_token");
  window.location.replace("/login.html");
  return new Error("AUTH_REQUIRED");
};

async function sendJson(path, method, payload) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload ?? {}),
  });
  if (response.status === 401) throw unauthorized();
  if (!response.ok) throw new Error(`${path} failed: HTTP ${response.status}`);
  return response.json();
}

async function getJson(path) {
  const response = await fetch(path, {
    headers: { Accept: "application/json", ...authHeaders() },
  });
  if (response.status === 401) throw unauthorized();
  if (!response.ok) throw new Error(`${path} failed: HTTP ${response.status}`);
  return response.json();
}

const notifyWorkflow = () => {
  if (typeof document !== "undefined" && typeof document.dispatchEvent === "function") {
    document.dispatchEvent(new Event("sentrix:workflow-updated"));
  }
};

const STATUS_CODES = {
  New: "NEW",
  Confirmed: "CONFIRMED",
  "In Progress": "IN_PROGRESS",
  Resolved: "RESOLVED",
  Reopened: "REOPENED",
  "Accepted Risk": "ACCEPTED_RISK",
  "False Positive": "FALSE_POSITIVE",
};

export async function createApiRepository() {
  if (!token()) throw new Error("AUTH_REQUIRED");
  const response = await fetch("/api/v1/bootstrap", {
    headers: { Accept: "application/json", ...authHeaders() },
  });
  if (response.status === 401) throw unauthorized();
  if (!response.ok) {
    throw new Error(`bootstrap failed: HTTP ${response.status}`);
  }
  const data = await response.json();
  const pendingCreates = new Map();

  const repository = {
    snapshot: () => structuredClone(data),

    createProject(input) {
      const project = {
        id: `project-${Date.now()}`,
        name: String(input.name ?? "").trim(),
        owner: input.owner?.trim() || "Maya Chen",
        status: "Active",
        scope: input.scope?.trim() || "Not configured",
        createdAt: new Date().toISOString().slice(0, 10),
      };
      data.projects.unshift(project);
      sendJson("/api/v1/projects", "POST", {
        name: project.name,
        owner: project.owner,
        scope: project.scope,
      })
        .then((saved) => Object.assign(project, saved))
        .catch((error) => console.error("SENTRIX createProject", error));
      return structuredClone(project);
    },

    archiveProject(projectId) {
      const project = data.projects.find((item) => item.id === projectId);
      if (!project) throw new Error("Project not found.");
      const previous = project.status;
      project.status = "Archived";
      sendJson(`/api/v1/projects/${projectId}/archive`, "POST", {})
        .then((saved) => Object.assign(project, saved))
        .catch((error) => {
          project.status = previous;
          console.error("SENTRIX archiveProject", error);
        });
      return structuredClone(project);
    },

    createTarget(input) {
      const target = {
        id: `target-${Date.now()}`,
        projectId: input.projectId,
        name: String(input.name ?? "").trim(),
        type: input.type || "Web",
        authorized: true,
        scope: input.scope?.trim() || "",
        status: "Monitored",
      };
      data.targets.unshift(target);
      sendJson("/api/v1/targets", "POST", {
        projectId: target.projectId,
        name: target.name,
        type: target.type,
        scope: target.scope,
        authorizationConfirmed: true,
      })
        .then((saved) => Object.assign(target, saved))
        .catch((error) => console.error("SENTRIX createTarget", error));
      return structuredClone(target);
    },

    createScan(input) {
      const target = data.targets.find((item) => item.id === input.targetId);
      const scan = {
        id: `scan-${Date.now()}`,
        projectId: target?.projectId ?? "",
        targetId: input.targetId,
        name: String(input.name ?? "").trim(),
        profile: input.profile || "External attack surface",
        status: "Queued",
        progress: 0,
        simulated: true,
        createdAt: new Date().toISOString(),
        completedAt: null,
      };
      data.scans.unshift(scan);
      const optimisticId = scan.id;
      const created = sendJson("/api/v1/scans", "POST", {
        targetId: scan.targetId,
        name: scan.name,
        profile: scan.profile,
      })
        .then((saved) => {
          Object.assign(scan, saved);
          pendingCreates.delete(optimisticId);
          return scan;
        })
        .catch((error) => {
          pendingCreates.delete(optimisticId);
          console.error("SENTRIX createScan", error);
          return scan;
        });
      pendingCreates.set(optimisticId, created);
      return structuredClone(scan);
    },

    runSimulatedScan(scanId) {
      const scan = data.scans.find((item) => item.id === scanId);
      if (!scan) throw new Error("Scan not found.");
      scan.status = "Running";
      scan.progress = 5;
      scan.completedAt = null;
      scan.error = null;
      const startedAt = Date.now();
      const notifyUpdated = () => {
        if (typeof document !== "undefined" && typeof document.dispatchEvent === "function") {
          document.dispatchEvent(new Event("sentrix:scan-updated"));
        }
      };
      const poll = async (actualId) => {
        if (Date.now() - startedAt > 90_000) {
          scan.status = "Failed";
          scan.progress = 100;
          scan.error = "Timed out waiting for the worker.";
          notifyUpdated();
          return;
        }
        try {
          const state = await getJson(`/api/v1/scans/${actualId}`);
          scan.status = state.status;
          scan.progress = state.progress;
          scan.completedAt = state.completedAt;
          scan.error = state.run?.error || null;
          for (const finding of state.findings || []) {
            const existing = data.findings.find((item) => item.id === finding.id);
            if (existing) Object.assign(existing, finding);
            else data.findings.unshift(finding);
          }
          if (state.status === "Completed" || state.status === "Failed") {
            notifyUpdated();
            return;
          }
        } catch (error) {
          console.error("SENTRIX scan poll", error);
        }
        setTimeout(() => poll(actualId), 1000);
      };
      const ready = pendingCreates.get(scanId) ?? Promise.resolve(scan);
      ready
        .then(() => {
          const actualId = scan.id;
          setTimeout(() => poll(actualId), 800);
        })
        .catch((error) => console.error("SENTRIX scan create wait", error));
      return structuredClone(scan);
    },

    async uploadArtifact(findingId, file) {
      const finding = data.findings.find((item) => item.id === findingId);
      if (!finding) throw new Error("Finding not found.");
      const response = await fetch("/api/v1/artifacts", {
        method: "POST",
        headers: {
          Authorization: authHeaders().Authorization,
          "Content-Type": "application/octet-stream",
          "X-Project-Id": finding.projectId,
        },
        body: await file.arrayBuffer(),
      });
      if (response.status === 401) throw unauthorized();
      if (!response.ok) throw new Error(`artifact upload failed: HTTP ${response.status}`);
      const saved = await response.json();
      finding.artifacts = finding.artifacts || [];
      if (!finding.artifacts.some((item) => item.sha256 === saved.sha256)) {
        finding.artifacts.push({ sha256: saved.sha256, size: saved.size });
      }
      notifyWorkflow();
      return saved;
    },

    async downloadArtifact(sha256) {
      const response = await fetch(`/api/v1/artifacts/${sha256}`, {
        headers: { Authorization: authHeaders().Authorization },
      });
      if (response.status === 401) throw unauthorized();
      if (!response.ok) throw new Error(`artifact download failed: HTTP ${response.status}`);
      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `sentrix-${sha256.slice(0, 12)}.bin`;
      link.click();
      URL.revokeObjectURL(link.href);
      return true;
    },

    createAnalysis(findingId) {
      const now = new Date().toISOString();
      const analysis = {
        id: `analysis-${Date.now()}`,
        findingId,
        model: "SENTRIX Risk Engine",
        version: "4.8.2",
        status: "Completed",
        confidence: 91,
        summary: "Mock analysis pending API confirmation.",
        limitations: "Mock inference for demonstration only; not a trained model result.",
        createdAt: now,
        simulated: true,
      };
      data.analyses.unshift(analysis);
      sendJson(`/api/v1/findings/${findingId}/analyses`, "POST", {})
        .then((saved) => Object.assign(analysis, saved))
        .catch((error) => console.error("SENTRIX createAnalysis", error));
      return structuredClone(analysis);
    },

    updateFindingStatus(findingId, status) {
      const finding = data.findings.find((item) => item.id === findingId);
      if (!finding) throw new Error("Finding not found.");
      const previous = finding.status;
      finding.status = status;
      sendJson(
        `/api/v1/findings/${findingId}/transitions`,
        "POST",
        {
          to: STATUS_CODES[status],
          reason: "Analyst status transition.",
        },
      )
        .then((saved) => Object.assign(finding, saved))
        .catch((error) => {
          finding.status = previous;
          console.error("SENTRIX updateFindingStatus", error);
        });
      return structuredClone(finding);
    },

    createRemediation(input) {
      const task = {
        id: `task-${Date.now()}`,
        findingId: input.findingId,
        assignee: input.assignee || "Maya Chen",
        dueDate: input.dueDate || "",
        status: "In Progress",
        notes: input.notes || "Demo remediation task",
        verification: null,
      };
      data.remediations.unshift(task);
      sendJson(`/api/v1/findings/${input.findingId}/remediations`, "POST", {
        assignee: task.assignee,
        dueDate: task.dueDate,
        notes: task.notes,
      })
        .then((saved) => Object.assign(task, saved))
        .catch((error) => console.error("SENTRIX createRemediation", error));
      return structuredClone(task);
    },

    verifyRemediation(remediationId, outcome) {
      const task = data.remediations.find((item) => item.id === remediationId);
      if (!task) throw new Error("Remediation not found.");
      const finding = data.findings.find((item) => item.id === task.findingId);
      const previousFindingStatus = finding?.status;
      task.status = "Completed";
      task.verification = outcome || "Verified";
      if (finding) finding.status = "Resolved";
      sendJson(`/api/v1/remediations/${remediationId}/verify`, "POST", {
        outcome: "VERIFIED",
        method: "MANUAL_REVIEW",
        notes: "Demo verification.",
      })
        .then((saved) => {
          Object.assign(task, saved);
          if (finding && saved.findingStatus) finding.status = saved.findingStatus;
          notifyWorkflow();
        })
        .catch((error) => {
          task.status = "In Progress";
          task.verification = null;
          if (finding && previousFindingStatus) finding.status = previousFindingStatus;
          console.error("SENTRIX verifyRemediation", error);
        });
      return structuredClone(task);
    },

    createReport(input) {
      const report = {
        id: `report-${Date.now()}`,
        projectId: input.projectId,
        scanId: input.scanId || null,
        title: String(input.title ?? "").trim(),
        status: "Draft",
        createdAt: new Date().toISOString(),
      };
      data.reports.unshift(report);
      sendJson("/api/v1/reports", "POST", {
        projectId: report.projectId,
        title: report.title,
        scanId: report.scanId,
      })
        .then((saved) => Object.assign(report, saved))
        .catch((error) => console.error("SENTRIX createReport", error));
      return structuredClone(report);
    },

    exportReportCsv(reportId) {
      const report = data.reports.find((item) => item.id === reportId);
      if (!report) throw new Error("Report not found.");
      const project = data.projects.find((item) => item.id === report.projectId);
      const findings = data.findings.filter((item) => item.projectId === report.projectId);
      const clean = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
      const rows = [
        ["SENTRIX report", report.title],
        ["Project", project?.name || ""],
        ["Scope", project?.scope || ""],
        [],
        ["Severity", "Status", "Finding", "Target", "Evidence"],
      ];
      for (const finding of findings) {
        const target = data.targets.find((item) => item.id === finding.targetId);
        rows.push([
          finding.severity,
          finding.status,
          finding.title,
          target?.name || "",
          finding.evidence,
        ]);
      }
      return rows.map((row) => row.map(clean).join(",")).join("\n");
    },

    publishReport(reportId) {
      const report = data.reports.find((item) => item.id === reportId);
      if (!report) throw new Error("Report not found.");
      report.status = "Published";
      sendJson(`/api/v1/reports/${reportId}/publish`, "POST", {})
        .then((saved) => Object.assign(report, saved))
        .catch((error) => console.error("SENTRIX publishReport", error));
      return structuredClone(report);
    },
  };

  return new Proxy(repository, {
    get(target, property) {
      if (property in target) return target[property];
      // A Proxy returned from an async function is inspected for `then`.
      // Returning a function here would make the repository look thenable and
      // break every `await createApiRepository()` call.
      if (property === "then") return undefined;
      return readOnly;
    },
  });
}
