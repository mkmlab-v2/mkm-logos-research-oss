# Appendix: Evidence & Reproduction

## Keywords
topological knowledge graph, digital humanities, symbolic atomization, counterfactual robustness, cross-domain event similarity

## Artifact Packet
- `onepager`: `C:\workspace\docs\final\artifacts\global_atom_network_academic_onepager_latest.json`
- `abstracts`: `C:\workspace\docs\final\artifacts\global_atom_network_submission_abstracts_latest.json`
- `kdd_template`: `C:\workspace\docs\final\artifacts\global_atom_kdd_submission_template_latest.json`
- `phase_report`: `C:\workspace\docs\final\artifacts\global_atom_network_core100_phase_transition_report_latest.json`
- `full_canon_batch_report`: `C:\workspace\docs\final\artifacts\global_atom_full_canon_batch_report_latest.json`
- `full_canon_consolidated_manifest`: `C:\workspace\docs\final\artifacts\global_atom_full_canon\global_atom_full_canon_consolidated_manifest_latest.json`
- `gate_summary`: `C:\workspace\docs\final\artifacts\multi_symbol_gate_summary_latest.json`
- `counterfactual_comparison`: `C:\workspace\docs\final\artifacts\multi_symbol_counterfactual_comparison_latest.json`

## Suggested Commands
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_full_canon_batch_v1.ps1 -UseEventSource`
- `py scripts/build_global_atom_full_canon_consolidated_manifest_v1.py`
- `py scripts/build_global_atom_full_canon_batch_report_v1.py --stages-json docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json --output-json docs/final/artifacts/global_atom_full_canon_batch_report_latest.json`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_submission_pack_v1.ps1`
