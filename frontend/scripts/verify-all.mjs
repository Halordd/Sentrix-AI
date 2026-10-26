/**
 * Run the project's verification steps as separate processes and report each
 * step's real exit code.
 *
 *   npm test                    unit + HTTP tests
 *   npm run verify:browser      headless browser workflows
 *
 * Exit code: 0 only when every step passed; 2 when no step failed but a step was
 * skipped because its tool was unavailable (browser missing); 1 when any step
 * failed. A skipped browser check is never reported as a pass.
 *
 * No external network access is needed: the tests and the browser check only use
 * loopback addresses.
 */
import { spawn } from "node:child_process";

const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
const isWindows = process.platform === "win32";

const STEPS = [
  { label: "unit + HTTP tests", args: ["test"], skippedCode: null },
  { label: "browser verification", args: ["run", "verify:browser"], skippedCode: 2 },
];

function runNpm(args) {
  return new Promise((resolve) => {
    // On Windows npm is a .cmd shim, so route it through cmd.exe rather than
    // shell:true (which would concatenate unescaped arguments).
    const child = isWindows
      ? spawn(process.env.ComSpec ?? "cmd.exe", ["/d", "/s", "/c", `npm ${args.join(" ")}`], { stdio: "inherit" })
      : spawn(npmCommand, args, { stdio: "inherit" });
    child.on("error", (error) => {
      console.error(`could not start npm: ${error.message}`);
      resolve(1);
    });
    child.on("exit", (code, signal) => {
      resolve(code ?? (signal ? 1 : 0));
    });
  });
}

function classify(step, code) {
  if (code === 0) return "PASS";
  if (step.skippedCode !== null && code === step.skippedCode) return "SKIPPED";
  return "FAIL";
}

const results = [];
for (const step of STEPS) {
  console.log(`\n=== ${step.label}: npm ${step.args.join(" ")} ===`);
  const code = await runNpm(step.args);
  results.push({ step, code, status: classify(step, code) });
}

console.log("\n=== verification summary ===");
for (const result of results) {
  const detail = result.status === "SKIPPED" ? " (tool unavailable, nothing verified)" : "";
  console.log(`${result.status.padEnd(8)} ${result.step.label.padEnd(24)} exit ${result.code}${detail}`);
}

const failed = results.filter((result) => result.status === "FAIL");
const skipped = results.filter((result) => result.status === "SKIPPED");
if (failed.length > 0) {
  console.log("\nRESULT: FAIL — at least one verification step failed");
  process.exit(1);
}
if (skipped.length > 0) {
  console.log("\nRESULT: PARTIAL — everything that could run passed, but a step was skipped");
  process.exit(2);
}
console.log("\nRESULT: PASS — every verification step passed");
