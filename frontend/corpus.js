const token = localStorage.getItem("sentrix_token");
if (!token) window.location.replace("/login.html");

const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[char]));

const badge = (value) => `<span class="${value ? "verified" : "unverified"}">${value ? "verified" : "unverified"}</span>`;

async function get(path) {
  const response = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (response.status === 401) {
    localStorage.removeItem("sentrix_token");
    window.location.replace("/login.html");
    throw new Error("authentication required");
  }
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

function table(headers, rows) {
  return `<table class="corpus-table"><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("") || `<tr><td colspan="${headers.length}" class="muted">No records.</td></tr>`}</tbody></table>`;
}

try {
  const [projects, candidates, findings] = await Promise.all([
    get("/api/v1/corpus/projects"),
    get("/api/v1/corpus/candidates?limit=500"),
    get("/api/v1/corpus/findings?limit=500"),
  ]);
  document.querySelector("#model-label").textContent = `Score label: ${projects.scoreLabel}`;
  const totalFindings = projects.targets.reduce((sum, target) => sum + target.findings, 0);
  document.querySelector("#summary").innerHTML = [
    ["PROJECT", projects.project.name],
    ["TARGETS", projects.targets.length],
    ["FINDINGS", totalFindings],
    ["CANDIDATES", candidates.candidates.length],
  ].map(([label, value]) => `<article class="corpus-card"><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join("");
  document.querySelector("#targets").innerHTML = table(
    ["Target", "Type", "Findings"],
    projects.targets.map((target) => `<tr><td>${esc(target.name)}</td><td>${esc(target.type)}</td><td>${esc(target.findings)}</td></tr>`),
  );
  document.querySelector("#candidates").innerHTML = table(
    ["Source", "Target", "Score", "Action", "Verified"],
    candidates.candidates.slice(0, 50).map((item) => `<tr><td>${esc(item.sourceId)}<br><span class="muted">${esc(item.title)}</span></td><td>${esc(item.target)}</td><td>${Number(item.score).toFixed(4)}</td><td>${esc(item.actionCode)}</td><td>${badge(item.verified)}</td></tr>`),
  );
  document.querySelector("#findings").innerHTML = table(
    ["Source", "Target", "Severity", "CWE", "Score", "Verified"],
    findings.findings.map((item) => `<tr><td>${esc(item.sourceId)}<br><span class="muted">${esc(item.title)}</span></td><td>${esc(item.targetId)}</td><td>${esc(item.severity)}</td><td>${esc(item.cwe || "")}</td><td>${item.score === null ? "—" : Number(item.score).toFixed(4)}</td><td>${badge(item.verified)}</td></tr>`),
  );
} catch (error) {
  document.querySelector("#corpus-error").textContent = error.message;
}
