import http from "node:http";

const port = Number(process.env.PORT || 3000);

function makeSajuLabel(value = "") {
  const text = String(value);
  const score = Array.from(text).reduce((sum, ch) => sum + ch.charCodeAt(0), 0);
  const stems = ["목", "화", "토", "금", "수"];
  return `${stems[score % stems.length]}기 편중 경향`;
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  if (req.method !== "POST" || req.url !== "/manseryeok/reference") {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ success: false, error: "not_found" }));
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
      res.end(JSON.stringify({ success: false, error: "invalid_json" }));
      return;
    }

    const birthDatetime = payload.birth_datetime;
    if (typeof birthDatetime !== "string" || birthDatetime.trim().length === 0) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ success: false, error: "birth_datetime is required" }));
      return;
    }

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        success: true,
        saju_label: makeSajuLabel(birthDatetime),
      }),
    );
  });
});

server.listen(port, () => {
  console.log(`hostinger-manseryeok-api running on port ${port}`);
});
