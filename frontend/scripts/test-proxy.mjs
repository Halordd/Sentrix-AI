/**
 * Local test proxy: serves the frontend source and forwards /api to the
 * deployed Nginx/API. Used only by browser parity checks so the latest source
 * can be verified before it is copied to /var/www/sentrix.
 *
 *   node scripts/test-proxy.mjs
 *   APP_URL=http://127.0.0.1:3100/ node scripts/browser-api-check.mjs
 */
import { createServer, request as httpRequest } from "node:http";
import { createStaticServer } from "../server.mjs";

const STATIC_PORT = Number(process.env.STATIC_PORT ?? 3101);
const PORT = Number(process.env.PORT ?? 3100);
const API_HOST = process.env.API_HOST ?? "10.20.10.10";
const API_PORT = Number(process.env.API_PORT ?? 80);

const staticServer = createStaticServer(process.cwd()).listen(STATIC_PORT, "127.0.0.1", () => {
  console.log(`static source server on http://127.0.0.1:${STATIC_PORT}`);
});

const proxy = createServer((req, res) => {
  if (req.url?.startsWith("/api/")) {
    const upstream = httpRequest(
      { host: API_HOST, port: API_PORT, path: req.url, method: req.method, headers: { ...req.headers, host: API_HOST } },
      (response) => {
        res.writeHead(response.statusCode ?? 502, response.headers);
        response.pipe(res);
      },
    );
    upstream.on("error", (error) => {
      res.writeHead(502, { "Content-Type": "text/plain" });
      res.end(`API proxy error: ${error.message}`);
    });
    req.pipe(upstream);
    return;
  }
  const downstream = httpRequest(
    { host: "127.0.0.1", port: STATIC_PORT, path: req.url, method: req.method, headers: req.headers },
    (response) => {
      res.writeHead(response.statusCode ?? 502, response.headers);
      response.pipe(res);
    },
  );
  downstream.on("error", (error) => {
    res.writeHead(502, { "Content-Type": "text/plain" });
    res.end(`static proxy error: ${error.message}`);
  });
  req.pipe(downstream);
});

proxy.listen(PORT, "127.0.0.1", () => {
  console.log(`test UI on http://127.0.0.1:${PORT}/ -> ${API_HOST}:${API_PORT}/api/`);
});

const shutdown = () => {
  proxy.close();
  staticServer.close();
  process.exit(0);
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
