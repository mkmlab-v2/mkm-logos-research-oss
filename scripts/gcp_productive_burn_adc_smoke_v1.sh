#!/bin/bash
# One Vertex call using user ADC (not Cloud Shell metadata SA).
set -euo pipefail
ADC="${HOME}/.config/gcloud/application_default_credentials.json"
if [[ ! -f "$ADC" ]]; then
  echo "Missing $ADC — run: gcloud auth application-default login" >&2
  exit 1
fi
export GOOGLE_APPLICATION_CREDENTIALS="$ADC"
export GOOGLE_CLOUD_QUOTA_PROJECT="gen-lang-client-0846393371"
pip install -q google-genai google-auth
python3 - <<'PY'
import json
from pathlib import Path
from google.auth import load_credentials_from_file
from google.auth.transport.requests import Request
from google import genai

adc = Path.home() / ".config/gcloud/application_default_credentials.json"
meta = json.loads(adc.read_text())
print("adc_type", meta.get("type"), "quota", meta.get("quota_project_id"))
scopes = ("https://www.googleapis.com/auth/cloud-platform",)
creds, _ = load_credentials_from_file(str(adc), scopes=scopes)
creds.refresh(Request())
print("cred_class", type(creds).__name__)
client = genai.Client(
    vertexai=True,
    project="gen-lang-client-0846393371",
    location="us-central1",
    credentials=creds,
)
resp = client.models.generate_content(model="gemini-2.5-pro", contents="[HYPO] reply OK one word")
text = getattr(resp, "text", None) or str(resp)
print("vertex_ok", text[:120])
PY
