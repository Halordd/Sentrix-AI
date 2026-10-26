import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { request } from "node:http";
import { createStaticServer } from "../server.mjs";

async function withServer(run) {
  const root = await mkdtemp(join(tmpdir(), "sentrix-static-"));
  await writeFile(join(root, "index.html"), "<h1>SENTRIX</h1>");
  await writeFile(join(root, "app.js"), "console.log('app');");
  await mkdir(join(root, ".dsh-acl-recovery"));
  await writeFile(join(root, ".dsh-acl-recovery", "acl-backup.json"), '{"secret":true}');
  const server = createStaticServer(root);
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const { port } = server.address();
  try {
    return await run(port);
  } finally {
    await new Promise((done) => server.close(done));
    await rm(root, { recursive: true, force: true });
  }
}

function send(port, path, method = "GET") {
  return new Promise((resolve, reject) => {
    const outgoing = request({ host: "127.0.0.1", port, path, method, agent: false }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => resolve({
        status: response.statusCode,
        headers: response.headers,
        body: Buffer.concat(chunks).toString("utf8"),
      }));
    });
    outgoing.on("error", reject);
    outgoing.end();
  });
}

test("serves a real asset with its content type", async () => {
  await withServer(async (port) => {
    const response = await send(port, "/");
    assert.equal(response.status, 200);
    assert.match(response.headers["content-type"], /text\/html/);
    assert.match(response.body, /SENTRIX/);
    assert.equal(response.headers["x-content-type-options"], "nosniff");
  });
});

test("returns 404 for a missing asset", async () => {
  await withServer(async (port) => {
    assert.equal((await send(port, "/missing.js")).status, 404);
  });
});

test("returns 403 for recovery artifacts and never leaks their body", async () => {
  await withServer(async (port) => {
    const response = await send(port, "/.dsh-acl-recovery/acl-backup.json");
    assert.equal(response.status, 403);
    assert.doesNotMatch(response.body, /secret/);
  });
});

test("returns 403 for traversal attempts", async () => {
  await withServer(async (port) => {
    assert.equal((await send(port, "/../index.html")).status, 403);
    assert.equal((await send(port, "/%2e%2e/index.html")).status, 403);
  });
});

test("returns 400 for invalid request targets", async () => {
  await withServer(async (port) => {
    assert.equal((await send(port, "/%zz")).status, 400);
    assert.equal((await send(port, "/..%5cindex.html")).status, 400);
  });
});

test("returns 405 for non-read methods", async () => {
  await withServer(async (port) => {
    const response = await send(port, "/", "POST");
    assert.equal(response.status, 405);
    assert.match(response.headers.allow, /GET/);
  });
});

test("HEAD returns headers without a body", async () => {
  await withServer(async (port) => {
    const response = await send(port, "/", "HEAD");
    assert.equal(response.status, 200);
    assert.equal(response.body, "");
    assert.ok(Number(response.headers["content-length"]) > 0);
  });
});

test("a directory junction inside the root cannot expose files outside it", async (t) => {
  const base = await mkdtemp(join(tmpdir(), "sentrix-link-"));
  const root = join(base, "root");
  const outside = join(base, "outside");
  await mkdir(root);
  await mkdir(outside);
  await writeFile(join(root, "index.html"), "<h1>root</h1>");
  await writeFile(join(outside, "secret.txt"), "OUTSIDE-SECRET");
  try {
    // Junctions are reparse points that do not need symlink privileges on Windows.
    await symlink(outside, join(root, "escape"), "junction");
  } catch (error) {
    await rm(base, { recursive: true, force: true });
    t.skip(`cannot create a directory junction in this environment: ${error.code}`);
    return;
  }
  const server = createStaticServer(root);
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const { port } = server.address();
  try {
    const response = await send(port, "/escape/secret.txt");
    assert.equal(response.status, 403);
    assert.doesNotMatch(response.body, /OUTSIDE-SECRET/);
  } finally {
    await new Promise((done) => server.close(done));
    await rm(base, { recursive: true, force: true });
  }
});

test("a file symlink inside the root cannot expose a file outside it", async (t) => {
  const base = await mkdtemp(join(tmpdir(), "sentrix-link-"));
  const root = join(base, "root");
  const outside = join(base, "outside");
  await mkdir(root);
  await mkdir(outside);
  await writeFile(join(root, "index.html"), "<h1>root</h1>");
  await writeFile(join(outside, "secret.txt"), "OUTSIDE-SECRET");
  try {
    await symlink(join(outside, "secret.txt"), join(root, "link.txt"), "file");
  } catch (error) {
    await rm(base, { recursive: true, force: true });
    t.skip(`file symlinks are not permitted in this environment: ${error.code}`);
    return;
  }
  const server = createStaticServer(root);
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const { port } = server.address();
  try {
    const response = await send(port, "/link.txt");
    assert.equal(response.status, 403);
    assert.doesNotMatch(response.body, /OUTSIDE-SECRET/);
  } finally {
    await new Promise((done) => server.close(done));
    await rm(base, { recursive: true, force: true });
  }
});
