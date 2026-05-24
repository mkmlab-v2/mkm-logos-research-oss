"""One-shot OPS webhook smoke (run on VPS with .env loaded)."""
import json
import os
import sys
from urllib import error, request

url = os.environ.get("OPS_ALARM_WEBHOOK_URL", "").strip()
if not url:
    print("SKIP no OPS_ALARM_WEBHOOK_URL")
    sys.exit(0)
body = {
    "source": "aroon_signal_webhook_smoke_v1",
    "symbol": "BTCUSDT",
    "previous_signal": "HOLD",
    "current_signal": "SMOKE_TEST",
    "note": "MKM ops smoke — not a real trade signal",
}
data = json.dumps(body, ensure_ascii=False).encode("utf-8")
req = request.Request(
    url, data=data, headers={"Content-Type": "application/json"}, method="POST"
)
try:
    with request.urlopen(req, timeout=15) as r:
        print("OK http", r.status)
except error.HTTPError as e:
    print("FAIL http", e.code)
    sys.exit(1)
except error.URLError as e:
    print("FAIL", e.reason)
    sys.exit(1)
