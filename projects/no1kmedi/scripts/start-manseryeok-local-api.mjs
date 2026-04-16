#!/usr/bin/env node
import http from "node:http";

const port = Number(process.env.MANSERYEOK_LOCAL_PORT || 8787);

function makeSajuLabel(birthDatetime = "") {
  const sum = Array.from(String(birthDatetime)).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const stems = ["목", "화", "토", "금", "수"];
  return `${stems[sum % stems.length]}기 편중 경향`;
}

const server = http.createServer((req, res) => {
  if (req.method !== "POST" || req.url !== "/manseryeok/reference") {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "not_found" }));
    return;
  }

  let body = "";
  req.on("data", (chunk) => {
    body += chunk.toString();
  });
  req.on("end", () => {
    let payload = {};
    try {
      payload = JSON.parse(body || "{}");
    } catch {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_json" }));
      return;
    }

    const label = makeSajuLabel(payload.birth_datetime);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ saju_label: label, source: "local-api" }));
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`local manseryeok api listening on http://127.0.0.1:${port}/manseryeok/reference`);
});
