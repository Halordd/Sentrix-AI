import { join, normalize, resolve, sep } from "node:path";

const rejected = (status, reason) => ({ status, reason });
const WINDOWS = process.platform === "win32";
const compare = (value) => (WINDOWS ? value.toLowerCase() : value);

/**
 * True when candidatePath is rootPath itself or strictly inside it.
 *
 * The comparison is separator-bounded, so a sibling whose name merely starts
 * with the root's name (root "app" vs "app-evil") is not contained. Call this
 * with real (resolved) paths for the filesystem check: lexical paths alone
 * cannot see through a junction or symlink that points outside the root.
 */
export function isContained(rootPath, candidatePath) {
  const root = compare(normalize(resolve(rootPath)));
  const candidate = compare(normalize(resolve(candidatePath)));
  if (candidate === root) return true;
  const prefix = root.endsWith(sep) ? root : root + sep;
  return candidate.startsWith(prefix);
}

/**
 * Classify a request URL against a static root before any file is opened.
 *
 * Returns { status: 200, filePath } or { status: 400 | 403, reason }:
 *   - 400: the request target is not a well-formed origin-form path
 *     (empty, malformed percent-encoding, NUL, or a backslash separator);
 *   - 403: the path is well formed but never served (a dot-prefixed segment,
 *     a "." / ".." segment, or a path that resolves outside the root).
 *
 * This is the lexical gate only. The server must also resolve the candidate
 * with realpath and re-check containment, because a junction or symlink inside
 * the root can point anywhere.
 */
export function classifyStaticRequest(root, requestUrl) {
  if (typeof requestUrl !== "string" || requestUrl.length === 0) return rejected(400, "empty request target");
  const [rawPath] = requestUrl.split("?");
  if (!rawPath) return rejected(400, "empty request target");
  if (rawPath.includes("\0") || rawPath.includes("\\")) return rejected(400, "invalid path separator");

  let pathname;
  try {
    pathname = decodeURIComponent(rawPath);
  } catch {
    return rejected(400, "malformed percent-encoding");
  }
  if (pathname.includes("\0") || pathname.includes("\\")) return rejected(400, "invalid path separator");
  if (!pathname.startsWith("/")) return rejected(400, "request target is not an origin-form path");
  if (pathname === "/") pathname = "/index.html";

  const segments = pathname.split("/").filter((segment) => segment.length > 0);
  if (segments.some((segment) => segment === "." || segment === ".." || segment.startsWith("."))) {
    return rejected(403, "hidden, relative or traversal path");
  }

  const rootPath = normalize(resolve(root));
  const filePath = normalize(join(rootPath, pathname));
  if (!isContained(rootPath, filePath)) return rejected(403, "path escapes the static root");

  return { status: 200, filePath };
}
