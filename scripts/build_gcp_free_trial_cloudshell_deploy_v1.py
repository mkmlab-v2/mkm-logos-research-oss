"""Build base64 paste one-liners for Cloud Shell burn deploy."""
from __future__ import annotations

import base64
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def b64_file(rel: str) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def main() -> None:
    burn_b64 = b64_file("scripts/gcp_free_trial_cloud_shell_burn_v1.sh")
    chain_b64 = b64_file("scripts/gcp_free_trial_cloud_shell_burn_chain_v1.sh")
    watchdog_b64 = b64_file("scripts/gcp_free_trial_cloud_shell_burn_watchdog_v1.sh")
    autoresume_b64 = b64_file("scripts/gcp_free_trial_cloud_shell_burn_autoresume_v1.sh")
    deploy_burn = (
        f"printf '%s' '{burn_b64}' | base64 -d > ~/gcp_burn.sh && "
        f"sed -i 's/\\r$//' ~/gcp_burn.sh && chmod +x ~/gcp_burn.sh && echo DEPLOY_BURN_OK"
    )
    deploy_chain = (
        f"printf '%s' '{chain_b64}' | base64 -d > ~/gcp_burn_chain.sh && "
        f"sed -i 's/\\r$//' ~/gcp_burn_chain.sh && chmod +x ~/gcp_burn_chain.sh && "
        f"nohup bash ~/gcp_burn_chain.sh > ~/gcp_burn_chain_nohup.log 2>&1 & echo CHAIN_PID=$!"
    )
    out = ROOT / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "gcp_burn_cloudshell_deploy.txt").write_text(deploy_burn + "\n", encoding="utf-8")
    (out / "gcp_burn_cloudshell_chain_deploy.txt").write_text(
        deploy_burn + " && " + deploy_chain + "\n", encoding="utf-8"
    )
    (out / "gcp_burn_cloudshell_chain_only.txt").write_text(deploy_chain + "\n", encoding="utf-8")
    deploy_watchdog = (
        f"printf '%s' '{watchdog_b64}' | base64 -d > ~/gcp_burn_watchdog.sh && "
        f"sed -i 's/\\r$//' ~/gcp_burn_watchdog.sh && chmod +x ~/gcp_burn_watchdog.sh && "
        f"nohup bash ~/gcp_burn_watchdog.sh > ~/gcp_burn_watchdog_nohup.log 2>&1 & echo WATCHDOG_PID=$!"
    )
    deploy_autoresume = (
        f"printf '%s' '{autoresume_b64}' | base64 -d > ~/gcp_burn_autoresume.sh && "
        f"sed -i 's/\\r$//' ~/gcp_burn_autoresume.sh && chmod +x ~/gcp_burn_autoresume.sh && "
        f"grep -q gcp_burn_autoresume ~/.bashrc 2>/dev/null || "
        f"echo 'bash ~/gcp_burn_autoresume.sh' >> ~/.bashrc && echo AUTORESUME_HOOK_OK"
    )
    (out / "gcp_burn_cloudshell_watchdog_deploy.txt").write_text(
        deploy_watchdog + " && " + deploy_autoresume + "\n", encoding="utf-8"
    )
    max_par_b64 = b64_file("scripts/gcp_free_trial_cloud_shell_max_burn_parallel_v1.sh")
    deploy_max_b64 = b64_file("scripts/gcp_free_trial_cloud_shell_max_burn_deploy_v1.sh")
    deploy_max = (
        f"printf '%s' '{burn_b64}' | base64 -d > ~/gcp_burn.sh && "
        f"sed -i 's/\\r$//' ~/gcp_burn.sh && chmod +x ~/gcp_burn.sh && "
        f"printf '%s' '{max_par_b64}' | base64 -d > ~/gcp_max_burn_parallel.sh && "
        f"sed -i 's/\\r$//' ~/gcp_max_burn_parallel.sh && chmod +x ~/gcp_max_burn_parallel.sh && "
        f"printf '%s' '{deploy_max_b64}' | base64 -d > ~/gcp_max_burn_deploy.sh && "
        f"sed -i 's/\\r$//' ~/gcp_max_burn_deploy.sh && chmod +x ~/gcp_max_burn_deploy.sh && "
        f"bash ~/gcp_max_burn_deploy.sh"
    )
    (out / "gcp_burn_cloudshell_max_deploy.txt").write_text(deploy_max + "\n", encoding="utf-8")
    print("wrote chain deploy", len(deploy_burn + deploy_chain))
    print("wrote watchdog deploy", len(deploy_watchdog + deploy_autoresume))
    print("wrote max deploy", len(deploy_max))


if __name__ == "__main__":
    main()
