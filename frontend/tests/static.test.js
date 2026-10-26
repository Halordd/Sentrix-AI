import test from "node:test";
import assert from "node:assert/strict";
import { join, resolve } from "node:path";
import { classifyStaticRequest, isContained } from "../static.js";

const root = resolve("project-root");
const classify = (url) => classifyStaticRequest(root, url);

test("containment is separator bounded and includes the root itself", () => {
  assert.equal(isContained(root, root), true);
  assert.equal(isContained(root, join(root, "app.js")), true);
  assert.equal(isContained(root, join(root, "nested", "deep", "file.js")), true);
  assert.equal(isContained(root, resolve("project-root-evil", "secret.txt")), false);
  assert.equal(isContained(root, resolve("other", "file.js")), false);
});

test("the root request resolves to index.html", () => {
  const result = classify("/");
  assert.equal(result.status, 200);
  assert.equal(result.filePath, join(root, "index.html"));
});

test("a query string is not part of the served path", () => {
  assert.equal(classify("/app.js?v=2").filePath, join(root, "app.js"));
});

test("recovery artifacts are never served", () => {
  for (const url of ["/.dsh-acl-recovery/acl-backup.json", "/.dsh-acl-recovery/", "/.dsh-acl-recovery/../index.html"]) {
    assert.equal(classify(url).status, 403, url);
  }
});

test("percent-encoded hidden segments are rejected", () => {
  assert.equal(classify("/%2edsh-acl-recovery/acl-backup.json").status, 403);
  assert.equal(classify("/%2E%64sh-acl-recovery/acl-backup.json").status, 403);
});

test("parent traversal is rejected", () => {
  assert.equal(classify("/../project-root-evil/secret.txt").status, 403);
  assert.equal(classify("/%2e%2e/project-root-evil/secret.txt").status, 403);
  assert.equal(classify("/..%2fproject-root-evil/secret.txt").status, 403);
});

test("alternate separators are rejected as invalid", () => {
  assert.equal(classify("/..\\index.html").status, 400);
  assert.equal(classify("/..%5cindex.html").status, 400);
});

test("malformed request targets are rejected as invalid", () => {
  assert.equal(classify("").status, 400);
  assert.equal(classify("/%zz").status, 400);
  assert.equal(classify("/%00").status, 400);
  assert.equal(classify("index.html").status, 400);
});
