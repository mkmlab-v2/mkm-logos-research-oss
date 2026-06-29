from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parts = [
    (ROOT / f"reports/cloudshell_wave2_b64_p{i}.txt").read_text(encoding="utf-8")
    for i in range(1, 5)
]
cmds = ["rm -f /tmp/w2.b64"]
for part in parts:
    cmds.append(f"printf '%s' '{part}' >> /tmp/w2.b64")
cmds.append("base64 -d /tmp/w2.b64 | bash")
out = ROOT / "reports/cloudshell_wave2_cmds.txt"
out.write_text("\n---CMD---\n".join(cmds), encoding="utf-8")
print(f"wrote {out} n={len(cmds)} max_len={max(len(c) for c in cmds)}")
