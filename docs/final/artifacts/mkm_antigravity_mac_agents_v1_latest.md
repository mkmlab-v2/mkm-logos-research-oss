# MKM Antigravity Mac Agents — latest pointer (v1)

**status:** ready_to_copy  
**generated:** 2026-07-13  
**role:** Mac Antigravity = design satellite only (not Cursor spine transplant)  
**send_gate:** HOLD (visual draft ≠ production merge)

## Drop-in (copy these)

| Artifact | Path |
|----------|------|
| Workspace rules | `docs/final/artifacts/antigravity_mac_dropin/.agents/AGENTS.md` |
| Skill | `docs/final/artifacts/antigravity_mac_dropin/.agents/skills/jema-design-pack/SKILL.md` |
| Install steps | `docs/final/artifacts/antigravity_mac_dropin/README_INSTALL_V1.md` |

## Related SSOT (PC)

- Ops card: `docs/final/MACBOOK_OPT_OPS_CARD_V1.md`
- Remote env §7: `docs/final/MACBOOK_REMOTE_DEV_ENV_V1.md`
- Pack prompts: `docs/final/artifacts/jemaai_antigravity_design_prompt_packs_v1_latest.md`
- Audit map: `docs/final/artifacts/jemaai_design_audit_surface_map_v1_latest.json`
- Design lane skill (Cursor): `.cursor/skills/mkm-design-lane/SKILL.md`

## Workflow (fixed)

```text
PC Cursor audit → Mac Antigravity visual draft → PC Cursor scoped merge + gates exit 0
```

## Mac one-liner

```bash
cp -R docs/final/artifacts/antigravity_mac_dropin/.agents /path/to/thin-design-root/
```

(Use Tailscale/USB/git sparse checkout to get `antigravity_mac_dropin` onto the Mac first.)
