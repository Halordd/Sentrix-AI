import { createReadStream, realpathSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, normalize, resolve } from "node:path";
import { classifyStaticRequest, isContained } from "./static.js";

const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
};

const isDenied = (error) => Boolean(error) && (error.code === "EACCES" || error.code === "EPERM");

// The native resolver follows Windows junctions; the JS realpathSync can return
// the link path itself, and lstat reports a junction as a directory rather than
// a symlink. Resolution must therefore use the native call, not lstat.
const resolveRealPath = (value) => realpathSync.native(value);

function respond(response, request, status, message, extraHeaders = {}) {
  const body = `${message}\n`;
  response.writeHead(status, {
    "Content-Type": "text/plain; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "X-Content-Type-Options": "nosniff",
    ...extraHeaders,
  });
  if (request.method === "HEAD") response.end();
  else response.end(body);
}

/**
 * Build the demo static server for a root directory.
 *
 * Only GET and HEAD are answered. A path must pass two gates: the lexical
 * classifier, then containment of its real path inside the real root. The
 * second gate is what stops a junction or symlink inside the root from
 * exposing a file outside it. A missing or unreadable file becomes 404 or 403.
 * A file stream error after the headers are on the wire destroys the response
 * instead of throwing, and a client disconnect destroys the stream, so neither
 * can crash the process.
 */
export function createStaticServer(root = process.cwd()) {
  const rootPath = normalize(resolve(root));
  let realRoot = null;
  try {
    realRoot = resolveRealPath(rootPath);
  } catch {
    realRoot = null;
  }

  return createServer((request, response) => {
    // Client disconnects surface as response errors; they are expected, not fatal.
    response.on("error", () => {});

    if (request.method !== "GET" && request.method !== "HEAD") {
      respond(response, request, 405, "Method Not Allowed", { Allow: "GET, HEAD" });
      return;
    }

    if (!realRoot) {
      respond(response, request, 404, "Not Found");
      return;
    }

    const classified = classifyStaticRequest(rootPath, request.url);
    if (classified.status !== 200) {
      respond(response, request, classified.status, classified.status === 403 ? "Forbidden" : "Bad Request");
      return;
    }

    // Resolve links before touching the file: a junction or symlink inside the
    // root may point at anything, and the lexical path cannot show that.
    let realFile;
    try {
      realFile = resolveRealPath(classified.filePath);
    } catch (error) {
      respond(response, request, isDenied(error) ? 403 : 404, isDenied(error) ? "Forbidden" : "Not Found");
      return;
    }
    if (!isContained(realRoot, realFile)) {
      respond(response, request, 403, "Forbidden");
      return;
    }

    let stats;
    try {
      stats = statSync(realFile);
    } catch (error) {
      respond(response, request, isDenied(error) ? 403 : 404, isDenied(error) ? "Forbidden" : "Not Found");
      return;
    }
    if (!stats.isFile()) {
      respond(response, request, 404, "Not Found");
      return;
    }

    response.writeHead(200, {
      "Content-Type": types[extname(realFile)] ?? "application/octet-stream",
      "Content-Length": stats.size,
      "X-Content-Type-Options": "nosniff",
    });
    if (request.method === "HEAD") {
      response.end();
      return;
    }

    const stream = createReadStream(realFile);
    stream.on("error", () => {
      if (response.headersSent) response.destroy();
      else respond(response, request, 500, "Internal Server Error");
    });
    response.on("close", () => stream.destroy());
    stream.pipe(response);
  });
}

// Loopback by default: this demo is not meant to be reachable from the network.
// HOST is an explicit opt-in for anyone who needs broader access.
if (import.meta.main) {
  const port = Number(process.env.PORT ?? 3000);
  const host = process.env.HOST ?? "127.0.0.1";
  createStaticServer(process.cwd()).listen(port, host, () => {
    console.log(`SENTRIX UI running at http://${host}:${port}`);
  });
}
