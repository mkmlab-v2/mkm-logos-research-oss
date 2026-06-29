from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parts = [
    (ROOT / f"reports/cloudshell_wave2_b64_p{i}.txt").read_text(encoding="utf-8")
    for i in range(1, 5)
]
cmds = ["rm -f /tmp/w2.b64"]
for part in parts:
    cmds.append(f"echo -n '{part}' >> /tmp/w2.b64")
cmds.append("base64 -d /tmp/w2.b64 | bash")
out = ROOT / "reports/cloudshell_wave2_cmds_echo.txt"
out.write_text("\n---CMD---\n".join(cmds), encoding="utf-8")
print(f"wrote {out} max_len={max(len(c) for c in cmds)}")
