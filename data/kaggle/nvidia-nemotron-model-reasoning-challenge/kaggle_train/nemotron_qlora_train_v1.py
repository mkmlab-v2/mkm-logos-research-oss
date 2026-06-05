#!/usr/bin/env python3
"""Nemotron competition QLoRA train — Kaggle GPU script kernel (no MKM core).

Reads train.csv from competition input on Kaggle or local data/kaggle/<slug>/.
Writes LoRA adapter + submission.zip under output dir. Does NOT call kaggle submit.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

DEFAULT_SLUG = "nvidia-nemotron-model-reasoning-challenge"
DEFAULT_BASE = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
# Kaggle default: tiny model, no mamba/pydeps storm (~15–40 min). Nemotron: set MKM_KAGGLE_TRAIN_PROFILE=nemotron.
FAST_SMOKE_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"
MAX_LORA_RANK = 32


def _is_kaggle() -> bool:
    return Path("/kaggle/input").is_dir()


def _kaggle_pydeps_root() -> Path:
    return Path("/kaggle/working/pydeps")


def _kaggle_scrub_stale_pydeps() -> None:
    """Prior failed runs leave broken torch wheels under pydeps on PYTHONPATH."""
    if not _is_kaggle():
        return
    dep = _kaggle_pydeps_root()
    if dep.is_dir():
        shutil.rmtree(dep, ignore_errors=True)
        print("[early] wiped stale /kaggle/working/pydeps (broken torch from prior runs)")
    os.environ.pop("PYTHONPATH", None)
    sys.path[:] = [p for p in sys.path if not p or Path(p).resolve() != dep.resolve()]


_kaggle_scrub_stale_pydeps()


def _kaggle_configure_hf_scratch_cache() -> None:
    """Keep ~63GB HF weights off /kaggle/working (20GB persistent cap); use session scratch."""
    if not _is_kaggle():
        return
    hf_root = Path("/kaggle/tmp/hf_hub")
    hf_root.mkdir(parents=True, exist_ok=True)
    Path("/kaggle/tmp/pip").mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf_root)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_root / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(hf_root / "transformers")
    os.environ["HF_DATASETS_CACHE"] = str(hf_root / "datasets")
    os.environ["TMPDIR"] = "/kaggle/tmp"
    os.environ["PIP_CACHE_DIR"] = "/kaggle/tmp/pip"
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    print("[early] HF hub cache -> /kaggle/tmp/hf_hub (not /kaggle/working)")
    legacy = Path("/root/.cache/huggingface")
    if legacy.is_dir():
        shutil.rmtree(legacy, ignore_errors=True)
        print("[early] removed legacy /root/.cache/huggingface (avoid 2x ~63GB)")


_kaggle_configure_hf_scratch_cache()


def _kaggle_ram_report(label: str = "") -> None:
    if not _is_kaggle():
        return
    try:
        import psutil

        v = psutil.virtual_memory()
        tag = f"{label} " if label else ""
        print(
            f"[ram] {tag}used={v.used / 1e9:.1f}GB avail={v.available / 1e9:.1f}GB total={v.total / 1e9:.1f}GB",
            flush=True,
        )
    except Exception as exc:
        print(f"[ram] {label}report skipped: {exc}", flush=True)


def _kaggle_free_before_model_load() -> None:
    if not _is_kaggle():
        return
    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except Exception:
        pass
    _kaggle_ram_report("before model load")


def _kaggle_nemotron_local_dir() -> Path:
    return Path("/kaggle/tmp/nemotron_hf_model")


def _bnb4bit_gpu_max_memory() -> dict[int, str]:
    """bitsandbytes 4bit: all layers must stay on GPU — no CPU/disk dispatch."""
    import torch

    out: dict[int, str] = {}
    for i in range(torch.cuda.device_count()):
        gib = torch.cuda.get_device_properties(i).total_memory / (1024**3)
        cap = max(12, int(gib - 1.5))
        out[i] = f"{cap}GiB"
    return out


def _warn_if_nemotron_vram_tight(args: argparse.Namespace) -> None:
    import torch

    if not _needs_4bit_training(args) or not torch.cuda.is_available():
        return
    n = torch.cuda.device_count()
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    total = sum(
        torch.cuda.get_device_properties(i).total_memory for i in range(n)
    ) / (1024**3)
    if total < 20:
        raise RuntimeError(
            f"Nemotron 30B QLoRA (4bit) needs ~20GB+ total VRAM; detected {n} GPU(s) "
            f"~{total:.1f}GB (primary {vram_gb:.1f}GB). "
            "5060 Ti 16GB / single-GPU WSL cannot load this model. "
            "Use Kaggle T4×2, cloud 24GB+ GPU, or local fast profile (SmolLM)."
        )
    if n == 1 and vram_gb < 22:
        print(
            f"[WARN] single GPU {vram_gb:.1f}GB — Nemotron 30B 4bit may OOM; "
            "24GB+ recommended",
            flush=True,
        )


def _accelerate_offload_dir(workspace: Path) -> Path:
    if _is_kaggle():
        d = Path("/kaggle/tmp/accelerate_offload")
    else:
        d = workspace / "storage" / "accelerate_offload"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _kaggle_disk_report(label: str = "") -> None:
    if not _is_kaggle():
        return
    import shutil

    tag = f"{label} " if label else ""
    for path in ("/kaggle/working", "/kaggle/tmp", "/"):
        try:
            u = shutil.disk_usage(path)
            print(
                f"[disk] {tag}{path}: "
                f"free={u.free / 1e9:.1f}GB used={u.used / 1e9:.1f}GB total={u.total / 1e9:.1f}GB",
                flush=True,
            )
        except OSError:
            pass


def _workspace_root() -> Path:
    if _is_kaggle():
        return Path("/kaggle/working")
    return Path(__file__).resolve().parents[4]


def _download_competition_train_csv(slug: str) -> Path:
    import subprocess

    dest = Path("/kaggle/working/comp_data")
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        ["kaggle", "competitions", "download", "-c", slug, "-f", "train.csv", "-p", str(dest)],
    )
    csv_path = dest / "train.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"kaggle download did not produce {csv_path}")
    return csv_path


def _resolve_kaggle_train_csv(slug: str) -> Path:
    base = Path("/kaggle/input")
    candidates = [
        base / slug / "train.csv",
        base / "train.csv",
    ]
    for c in candidates:
        if c.is_file():
            return c
    if base.is_dir():
        found = sorted(base.rglob("train.csv"))
        if len(found) == 1:
            return found[0]
        if found:
            for p in found:
                if slug.replace("-", "") in str(p).replace("-", "").lower():
                    return p
            return found[0]
    print(f"[WARN] train.csv not in /kaggle/input; downloading via kaggle CLI (slug={slug})")
    return _download_competition_train_csv(slug)


def _default_train_csv(slug: str, workspace: Path) -> Path:
    if _is_kaggle():
        return _resolve_kaggle_train_csv(slug)
    return workspace / "data" / "kaggle" / slug / "train.csv"


def _default_out_dir(workspace: Path) -> Path:
    if _is_kaggle():
        return Path("/kaggle/working/nemotron_adapter")
    return workspace / "data" / "kaggle" / DEFAULT_SLUG / "kaggle_train" / "output"


def _boxed_answer(answer: str) -> str:
    a = (answer or "").strip()
    if a.startswith("\\boxed{") and a.endswith("}"):
        return a
    return f"\\boxed{{{a}}}"


def _prefetch_hub_model_if_kaggle(model_id: str) -> Path | None:
    """Download once to /kaggle/tmp/nemotron_hf_model; from_pretrained uses local_files_only."""
    if not _is_kaggle():
        return None
    import shutil

    _kaggle_disk_report("before prefetch")
    _kaggle_ram_report("before prefetch")
    tmp_free = shutil.disk_usage("/kaggle/tmp").free
    if tmp_free < 55 * 1e9:
        raise RuntimeError(
            f"/kaggle/tmp free {tmp_free / 1e9:.1f}GB — need ~55GB+ for Nemotron BF16 (~63GB). "
            "Session Restart → rm -rf /kaggle/tmp/hf_hub /kaggle/tmp/nemotron_hf_model "
            "/root/.cache/huggingface → v44+ cell."
        )
    local_dir = _kaggle_nemotron_local_dir()
    if local_dir.is_dir() and (local_dir / "config.json").is_file():
        print(f"[train] hub cache hit: {local_dir}", flush=True)
        _kaggle_disk_report("prefetch hit")
        return local_dir
    if local_dir.is_dir():
        shutil.rmtree(local_dir, ignore_errors=True)
    print(f"[train] hub prefetch start: {model_id} -> {local_dir}", flush=True)
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=model_id,
        repo_type="model",
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    _kaggle_disk_report("after prefetch")
    import gc

    gc.collect()
    _kaggle_ram_report("after prefetch gc")
    print(f"[train] hub prefetch done: {local_dir}", flush=True)
    return local_dir


def _hf_login_if_needed() -> None:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token and _is_kaggle():
        try:
            from kaggle_secrets import UserSecretsClient

            token = UserSecretsClient().get_secret("HF_TOKEN")
        except Exception:
            token = None
    if token:
        from huggingface_hub import login

        login(token=token, add_to_git_credential=False)


def _cxx11_abi_tag() -> str:
    import torch

    return "TRUE" if torch._C._GLIBCXX_USE_CXX11_ABI else "FALSE"


def _torch_mamba_wheel_tag() -> str:
    import torch

    ver = torch.__version__.split("+")[0]
    parts = ver.split(".")
    minor = parts[1] if len(parts) > 1 else "0"
    return f"cu12torch{parts[0]}.{minor}"


def _install_mamba_kaggle_wheels() -> None:
    """Install prebuilt causal-conv1d + mamba-ssm wheels (avoid source build on Kaggle)."""
    import subprocess
    import urllib.request

    import torch

    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    platform_tag = "linux_x86_64"
    torch_tag = _torch_mamba_wheel_tag()
    abi_primary = _cxx11_abi_tag()
    abi_order = [abi_primary, "TRUE" if abi_primary == "FALSE" else "FALSE"]

    torch_fallbacks = [torch_tag]
    for fb in ("cu12torch2.10", "cu12torch2.9", "cu12torch2.8", "cu12torch2.7", "cu12torch2.6"):
        if fb not in torch_fallbacks:
            torch_fallbacks.append(fb)

    causal_base = "https://github.com/Dao-AILab/causal-conv1d/releases/download/v1.6.2.post1"
    mamba_base = "https://github.com/state-spaces/mamba/releases/download/v2.3.2.post1"
    wheel_dir = Path("/kaggle/working/mamba_wheels")
    wheel_dir.mkdir(parents=True, exist_ok=True)

    def _pip_install(wheel_path: Path) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", str(wheel_path)])

    def _download(url: str, dest: Path) -> bool:
        try:
            print(f"[deps] downloading {url}")
            urllib.request.urlretrieve(url, dest)
            return dest.is_file() and dest.stat().st_size > 0
        except Exception as exc:
            print(f"[deps] download failed: {url} ({exc})")
            if dest.is_file():
                dest.unlink(missing_ok=True)
            return False

    for tt in torch_fallbacks:
        for abi in abi_order:
            causal_name = f"causal_conv1d-1.6.2.post1+{tt}cxx11abi{abi}-{py_tag}-{py_tag}-{platform_tag}.whl"
            mamba_name = f"mamba_ssm-2.3.2.post1+{tt}cxx11abi{abi}-{py_tag}-{py_tag}-{platform_tag}.whl"
            causal_path = wheel_dir / causal_name
            mamba_path = wheel_dir / mamba_name
            if not causal_path.is_file():
                if not _download(f"{causal_base}/{causal_name}", causal_path):
                    continue
            if not mamba_path.is_file():
                if not _download(f"{mamba_base}/{mamba_name}", mamba_path):
                    continue
            try:
                _pip_install(causal_path)
                _pip_install(mamba_path)
                _verify_mamba_import()
                shutil.rmtree(wheel_dir, ignore_errors=True)
                print(f"[deps] mamba wheels ok (torch_tag={tt}, abi={abi}); removed {wheel_dir}")
                return
            except Exception as exc:
                print(f"[deps] wheel install/import failed torch_tag={tt} abi={abi}: {exc}")

    raise RuntimeError(
        "mamba-ssm install failed on Kaggle. Nemotron hybrid needs causal-conv1d+mamba-ssm. "
        f"Tried torch tags={torch_fallbacks}, py={py_tag}, torch={torch.__version__}"
    )


def _verify_mamba_import() -> None:
    import mamba_ssm  # noqa: F401

    print(f"[deps] mamba_ssm ok from {mamba_ssm.__file__}")


def _gpu_capability() -> tuple[int, int]:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_capability(0)
    except Exception:
        pass
    return (0, 0)


def _kaggle_train_profile() -> str:
    if not _is_kaggle():
        return "local"
    if os.environ.get("MKM_KAGGLE_FULL", "").strip().lower() in ("1", "true", "yes"):
        return "nemotron"
    p = os.environ.get("MKM_KAGGLE_TRAIN_PROFILE", "fast").strip().lower()
    if p in ("nemotron", "full", "30b", "nano"):
        return "nemotron"
    return "fast"


def _apply_kaggle_profile_defaults(args: argparse.Namespace) -> str:
    profile = _kaggle_train_profile()
    if profile == "nemotron":
        print(
            f"[profile] nemotron 30B: model={args.base_model} "
            f"smoke={args.smoke} rows_cap={args.smoke_rows if args.smoke else 'all'} "
            f"(MKM_KAGGLE_FULL=1 and no --smoke for full train)"
        )
        return profile
    if profile != "fast":
        return profile
    args.base_model = FAST_SMOKE_MODEL
    args.smoke = True
    args.smoke_rows = min(args.smoke_rows, 8)
    args.smoke_steps = min(args.smoke_steps, 5)
    args.max_seq_len = min(args.max_seq_len, 384)
    args.lora_rank = min(args.lora_rank, 8)
    args.grad_accum = min(args.grad_accum, 4)
    print(
        f"[profile] fast pipeline smoke: model={args.base_model} rows={args.smoke_rows} "
        f"steps={args.smoke_steps} (set MKM_KAGGLE_TRAIN_PROFILE=nemotron for 30B)"
    )
    return profile


def _needs_4bit_training(args: argparse.Namespace) -> bool:
    if _is_kaggle() and _kaggle_train_profile() == "fast":
        return False
    name = args.base_model.lower()
    return any(tag in name for tag in ("nemotron", "30b", "nano-30", "a3b"))


def _bnb_modules_to_not_convert(base_model: str) -> list[str]:
    """Skip 4bit on layers whose raw .weight tensors feed mamba triton fused ops.

    Nemotron-H Mamba2 passes out_proj.weight into mamba_split_conv1d_scan_combined;
    Params4bit breaks F.linear (mat1 x mat2 shape mismatch). Keep out_proj fp16/bf16.

    Note: BitsAndBytesConfig uses ``llm_int8_skip_modules`` for both 8bit and 4bit
    (``modules_to_not_convert`` is ignored by the bnb 4bit quantizer).
    """
    name = base_model.lower()
    if not any(tag in name for tag in ("nemotron", "30b", "nano-30", "a3b", "mamba")):
        return ["lm_head"]
    return ["out_proj", "lm_head"]


def _patch_nemotron_mamba_bnb_fused_disable(model) -> int:
    """When out_proj stays 4bit, disable fused mamba kernel (uses raw .weight in F.linear)."""
    try:
        from bitsandbytes.nn import Params4bit
    except ImportError:
        return 0

    import types

    patched = 0
    for module in model.modules():
        if module.__class__.__name__ != "NemotronHMamba2Mixer":
            continue
        out_proj = getattr(module, "out_proj", None)
        weight = getattr(out_proj, "weight", None) if out_proj is not None else None
        if not isinstance(weight, Params4bit):
            continue
        orig_cuda = module.cuda_kernels_forward

        def cuda_kernels_forward_patched(
            self,
            hidden_states,
            cache_params,
            cache_position,
            attention_mask,
            _orig=orig_cuda,
        ):
            was_training = self.training
            if was_training and cache_params is None:
                self.training = False
                try:
                    return _orig(self, hidden_states, cache_params, cache_position, attention_mask)
                finally:
                    self.training = was_training
            return _orig(self, hidden_states, cache_params, cache_position, attention_mask)

        module.cuda_kernels_forward = types.MethodType(cuda_kernels_forward_patched, module)
        patched += 1
    return patched


def _patch_nemotron_moe_index_add_dtype(model) -> int:
    """MoE moe() uses topk_weights.dtype for accum buffer; router weights are fp32 under QLoRA."""
    import types

    import torch
    import torch.nn.functional as F

    patched = 0
    for module in model.modules():
        if module.__class__.__name__ != "NemotronHMOE":
            continue

        def moe_fixed(self, hidden_states, topk_indices, topk_weights):
            final_hidden_states = torch.zeros_like(hidden_states)
            expert_mask = F.one_hot(topk_indices, num_classes=len(self.experts))
            expert_mask = expert_mask.permute(2, 0, 1)
            for expert_idx in range(len(self.experts)):
                expert = self.experts[expert_idx]
                mask = expert_mask[expert_idx]
                token_indices, weight_indices = torch.where(mask)
                if token_indices.numel() > 0:
                    expert_weights = topk_weights[token_indices, weight_indices].to(
                        dtype=hidden_states.dtype
                    )
                    expert_input = hidden_states[token_indices]
                    expert_output = expert(expert_input)
                    weighted_output = (
                        expert_output * expert_weights.unsqueeze(-1)
                    ).to(dtype=hidden_states.dtype)
                    final_hidden_states.index_add_(0, token_indices, weighted_output)
                else:
                    expert_dtype = expert.down_proj.weight.dtype
                    dummy_out = expert(
                        torch.zeros_like(hidden_states[0]).unsqueeze(0).to(expert_dtype)
                    )
                    final_hidden_states = final_hidden_states + dummy_out.to(hidden_states.dtype)
            return final_hidden_states.type(hidden_states.dtype)

        module.moe = types.MethodType(moe_fixed, module)
        patched += 1
    return patched


def _apply_nemotron_qlora_runtime_patches(model) -> None:
    n_mamba = _patch_nemotron_mamba_bnb_fused_disable(model)
    if n_mamba:
        print(
            f"[train] patched {n_mamba} NemotronHMamba2Mixer (bnb fused fallback)",
            flush=True,
        )
    n_moe = _patch_nemotron_moe_index_add_dtype(model)
    if n_moe:
        print(f"[train] patched {n_moe} NemotronHMOE (dtype-safe index_add)", flush=True)


def _ensure_kaggle_deps_lite() -> None:
    """Fast profile: system torch + optional minimal pydeps; no mamba/unsloth/bnb pip storm."""
    if not _is_kaggle():
        return
    _kaggle_scrub_stale_pydeps()
    _prepare_kaggle_import_env()
    _bootstrap_kaggle_torch_isolation()
    cap = _gpu_capability()
    print(f"[deps-lite] kaggle gpu capability={cap}")
    if cap[0] < 7:
        raise RuntimeError(
            "Kaggle scheduled P100/sm_60 — needs GPU T4 x2. "
            "Settings → Accelerator → GPU T4 x2 → Save & Run All."
        )
    import importlib

    import transformers as _tf  # noqa: F401

    _lite_specs = (
        ("peft", "peft"),
        ("datasets", "datasets==3.6.0"),
        ("trl", "trl"),
        ("accelerate", "accelerate"),
    )
    missing: list[str] = []
    for mod, spec in _lite_specs:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(spec)
    if not missing:
        print(f"[deps-lite] Kaggle preinstalled stack ok (transformers {_tf.__version__})")
        return

    print(f"[deps-lite] installing to pydeps: {missing}")
    kaggle_pydeps = _kaggle_pydeps_root()
    kaggle_pydeps.mkdir(parents=True, exist_ok=True)
    dep_root = str(kaggle_pydeps.resolve())
    import subprocess

    def _pip_to_pydeps(pkgs: list[str], *, no_deps: bool) -> None:
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--no-cache-dir",
            "--target",
            dep_root,
        ]
        if no_deps:
            cmd.append("--no-deps")
        cmd.extend(pkgs)
        subprocess.check_call(cmd)

    def _import_missing_pydeps() -> None:
        for mod, spec in _lite_specs:
            if spec in missing:
                importlib.import_module(mod)

    _pip_to_pydeps(missing, no_deps=True)
    _append_kaggle_pydeps_to_syspath(dep_root)
    _verify_system_torch_after_pydeps()
    try:
        _import_missing_pydeps()
    except ImportError as exc:
        print(f"[deps-lite] --no-deps import failed ({exc}); retry pip with deps, strip torch wheels only")
        _pip_to_pydeps(missing, no_deps=False)
        _verify_system_torch_after_pydeps()
        _import_missing_pydeps()
    print("[deps-lite] minimal pydeps install ok")


def _ensure_kaggle_deps_for_profile(profile: str) -> None:
    if profile == "fast":
        _ensure_kaggle_deps_lite()
    else:
        _ensure_kaggle_deps()


def _use_unsloth_on_kaggle() -> bool:
    if not _is_kaggle():
        return False
    # Default off: unsloth from pydeps clashes with Kaggle's preinstalled torch
    # (RuntimeError: '_has_torch_function' already has a docstring).
    if os.environ.get("MKM_KAGGLE_USE_UNSLOTH", "").strip().lower() not in ("1", "true", "yes"):
        return False
    return _gpu_capability()[0] >= 7


# Kaggle ships torch in /usr/local; pip --target must not shadow it (torchvision in pydeps breaks trl).
_PYDEPS_STRIP_PREFIXES = ("torch", "torchvision", "torchaudio", "triton", "torchao")


def _kaggle_pydeps_datasets_loaded() -> bool:
    mod = sys.modules.get("datasets")
    if mod is None:
        return False
    f = str(getattr(mod, "__file__", "") or "").replace("\\", "/")
    dep = str(_kaggle_pydeps_root().resolve()).replace("\\", "/")
    return dep in f


def _kaggle_pydeps_bitsandbytes_loaded() -> bool:
    mod = sys.modules.get("bitsandbytes")
    if mod is None:
        return False
    f = str(getattr(mod, "__file__", "") or "").replace("\\", "/")
    dep = str(_kaggle_pydeps_root().resolve()).replace("\\", "/")
    return dep in f


def _purge_imported_modules(prefix: str) -> None:
    # trl probe imports datasets; purge leaves PyArrow extensions registered → ArrowKeyError on re-import.
    if _is_kaggle() and prefix == "datasets" and _kaggle_pydeps_datasets_loaded():
        return
    # bitsandbytes registers torch ops at first import; purge + re-import → duplicate op registration.
    if _is_kaggle() and prefix == "bitsandbytes" and _kaggle_pydeps_bitsandbytes_loaded():
        return
    if _is_kaggle() and prefix == "bitsandbytes" and "bitsandbytes" in sys.modules:
        return
    names = [n for n in sys.modules if n == prefix or n.startswith(f"{prefix}.")]
    for name in sorted(names, key=len, reverse=True):
        sys.modules.pop(name, None)


def _import_datasets_dataset():
    """Single pydeps datasets import per Kaggle session (do not purge after load)."""
    if _is_kaggle():
        _prepare_kaggle_import_env()
        dep_root = str(_kaggle_pydeps_root().resolve())
        if not _kaggle_pydeps_datasets_loaded():
            _purge_imported_modules("datasets")
            _prepend_kaggle_pydeps_hf_stack(dep_root)
    from datasets import Dataset

    if _is_kaggle():
        ds_mod = sys.modules.get("datasets")
        if ds_mod is not None:
            print(
                f"[deps] datasets ok ({ds_mod.__version__} @ {getattr(ds_mod, '__file__', '')})",
                flush=True,
            )
    return Dataset


def _prepare_kaggle_import_env() -> None:
    """Reduce vision/torch wheel clashes with Kaggle's preinstalled CUDA torch."""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["USE_TF"] = "0"
    os.environ["USE_TORCHVISION"] = "0"
    os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"
    os.environ["TRANSFORMERS_NO_TF"] = "1"
    if _is_kaggle():
        _patch_kaggle_inspect_getfile_v1()
        _block_kaggle_torchvision_import()


def _patch_kaggle_inspect_getfile_v1() -> None:
    """tilelang/torch patch inspect.getfile; torchvision register_fake then crashes on HF lazy modules."""
    import inspect

    current = inspect.getfile
    if getattr(current, "_mkm_kaggle_inspect_v1", False):
        return

    def _safe_getfile(object):  # noqa: ANN001
        try:
            return current(object)
        except TypeError as exc:
            if "built-in module" not in str(exc).lower():
                raise
            path = getattr(object, "__file__", None)
            if path:
                return path
            name = getattr(object, "__name__", "unknown")
            return f"/kaggle/working/_inspect_stub/{name.replace('.', '_')}.py"

    _safe_getfile._mkm_kaggle_inspect_v1 = True  # type: ignore[attr-defined]
    inspect.getfile = _safe_getfile


def _purge_kaggle_torchvision_modules() -> None:
    if not _is_kaggle():
        return
    for name in list(sys.modules):
        if name == "torchvision" or name.startswith("torchvision."):
            sys.modules.pop(name, None)


def _install_kaggle_torchvision_stub() -> None:
    """Stub torchvision with valid __spec__ (broken stub breaks importlib.util.find_spec)."""
    if not _is_kaggle():
        return
    import importlib.machinery
    import types

    _purge_kaggle_torchvision_modules()
    stub_root = "/kaggle/working/_kaggle_stub/torchvision"
    transforms_py = f"{stub_root}/transforms.py"
    pkg_init = f"{stub_root}/__init__.py"

    transforms = types.ModuleType("torchvision.transforms")
    transforms.__file__ = transforms_py
    transforms.InterpolationMode = types.SimpleNamespace(
        NEAREST_EXACT="nearest-exact",
        BOX="box",
        BILINEAR="bilinear",
        HAMMING="hamming",
        BICUBIC="bicubic",
        LANCZOS="lanczos",
    )
    transforms.__spec__ = importlib.machinery.ModuleSpec(
        "torchvision.transforms", loader=None, origin=transforms_py
    )

    tv = types.ModuleType("torchvision")
    tv.__file__ = pkg_init
    tv.__path__ = [stub_root]
    tv.transforms = transforms
    tv_spec = importlib.machinery.ModuleSpec("torchvision", loader=None, origin=pkg_init, is_package=True)
    tv_spec.submodule_search_locations = [stub_root]
    tv.__spec__ = tv_spec

    io_py = f"{stub_root}/io.py"
    io_mod = types.ModuleType("torchvision.io")
    io_mod.__file__ = io_py
    io_mod.__spec__ = importlib.machinery.ModuleSpec("torchvision.io", loader=None, origin=io_py)
    tv.io = io_mod

    sys.modules["torchvision.transforms"] = transforms
    sys.modules["torchvision.io"] = io_mod
    sys.modules["torchvision"] = tv


def _patch_transformers_skip_torchvision() -> None:
    """Force pydeps/system transformers to treat torchvision as absent (stub only satisfies find_spec)."""
    if not _is_kaggle():
        return
    _install_kaggle_torchvision_stub()
    _patch_system_transformers_torchvision_probe()

    def _vision_unavailable(*_args: object, **_kwargs: object) -> bool:
        return False

    patched = 0
    for mod_name in ("transformers.utils.import_utils", "transformers.utils"):
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        if hasattr(mod, "_torchvision_available"):
            mod._torchvision_available = False
        if hasattr(mod, "is_torchvision_available"):
            mod.is_torchvision_available = _vision_unavailable  # type: ignore[method-assign]
            cache_clear = getattr(mod.is_torchvision_available, "cache_clear", None)
            if callable(cache_clear):
                cache_clear()
        if hasattr(mod, "is_vision_available"):
            mod.is_vision_available = _vision_unavailable  # type: ignore[method-assign]
        patched += 1

    try:
        import transformers.utils.import_utils as iu
        import transformers.utils as tu

        iu._torchvision_available = False
        iu.is_torchvision_available = _vision_unavailable  # type: ignore[method-assign]
        cache_clear = getattr(iu.is_torchvision_available, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()
        tu.is_torchvision_available = iu.is_torchvision_available  # type: ignore[attr-defined]
        if hasattr(iu, "is_vision_available"):
            iu.is_vision_available = _vision_unavailable  # type: ignore[method-assign]
            tu.is_vision_available = iu.is_vision_available  # type: ignore[attr-defined]
        patched += 1
    except Exception as exc:
        print(f"[deps] warn: torchvision patch partial ({exc})")
        return

    if patched:
        print("[deps] torchvision blocked for transformers (stub + import_utils flag)")


def _patch_system_transformers_torchvision_probe() -> None:
    """mamba_ssm imports /usr/local transformers before pydeps; disable torchvision probe."""
    if not _is_kaggle():
        return
    try:
        import transformers.utils.import_utils as iu

        iu._torchvision_available = False

        def _torchvision_unavailable(*_args: object, **_kwargs: object) -> bool:
            return False

        iu.is_torchvision_available = _torchvision_unavailable  # type: ignore[method-assign]
        cache_clear = getattr(iu.is_torchvision_available, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()
    except Exception as exc:
        print(f"[deps] warn: system transformers torchvision patch ({exc})")


def _block_kaggle_torchvision_import() -> None:
    """Prevent real /usr/local torchvision from loading during transformers image_utils import."""
    _install_kaggle_torchvision_stub()
    _patch_system_transformers_torchvision_probe()


def _torch_is_kaggle_system_loaded() -> bool:
    torch_mod = sys.modules.get("torch")
    if torch_mod is None:
        return False
    tfile = str(getattr(torch_mod, "__file__", "") or "").replace("\\", "/")
    return "/usr/local/" in tfile


def _bootstrap_kaggle_torch_isolation() -> None:
    """Use Kaggle /usr/local torch only; clear pydeps shadowing from prior runs or notebook env."""
    dep = _kaggle_pydeps_root().resolve()
    py_paths = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [p for p in py_paths if Path(p).resolve() != dep]
    )
    sys.path[:] = [p for p in sys.path if not p or Path(p).resolve() != dep]
    if dep.is_dir():
        _strip_pydeps_torch_stack(dep, purge_modules=False)

    if _torch_is_kaggle_system_loaded():
        torch_mod = sys.modules["torch"]
        print(
            f"[deps] keep system torch {torch_mod.__version__} @ {getattr(torch_mod, '__file__', '')}"
        )
        return

    for prefix in _PYDEPS_STRIP_PREFIXES:
        _purge_imported_modules(prefix)
    import torch

    tfile = str(getattr(torch, "__file__", "") or "").replace("\\", "/")
    if "/usr/local/" not in tfile:
        raise RuntimeError(f"Expected Kaggle system torch under /usr/local, got {tfile}")
    print(f"[deps] locked system torch {torch.__version__} @ {torch.__file__}")


def _append_kaggle_pydeps_to_syspath(dep_root: str | None = None) -> str:
    """Append pydeps last so system site-packages (torch) win (fast/lite path)."""
    root = dep_root or str(_kaggle_pydeps_root().resolve())
    dep_path = Path(root).resolve()
    sys.path[:] = [p for p in sys.path if not p or Path(p).resolve() != dep_path]
    if root not in sys.path:
        sys.path.append(root)
    return root


def _prepend_kaggle_pydeps_hf_stack(dep_root: str | None = None) -> str:
    """Prepend pydeps so huggingface_hub/transformers/trl win; torch wheels must stay stripped from pydeps."""
    root = dep_root or str(_kaggle_pydeps_root().resolve())
    dep_path = Path(root).resolve()
    sys.path[:] = [p for p in sys.path if not p or Path(p).resolve() != dep_path]
    sys.path.insert(0, str(dep_path))
    return root


_HF_STACK_MODULES = (
    "huggingface_hub",
    "transformers",
    "tokenizers",
    "peft",
    "trl",
    "datasets",
    "accelerate",
    "bitsandbytes",
    "unsloth",
    "einops",
    "sentencepiece",
)


def _verify_pydeps_huggingface_hub(dep_root: str, *, minimum: str = "1.13.0") -> None:
    for mod in _HF_STACK_MODULES:
        _purge_imported_modules(mod)
    _prepend_kaggle_pydeps_hf_stack(dep_root)
    import huggingface_hub

    hub_ver = huggingface_hub.__version__
    hub_file = str(getattr(huggingface_hub, "__file__", "") or "").replace("\\", "/")
    dep_norm = str(Path(dep_root).resolve()).replace("\\", "/")
    if not _hub_version_at_least(hub_ver, minimum) or dep_norm not in hub_file:
        raise RuntimeError(
            f"Kaggle still on old huggingface_hub {hub_ver} ({hub_file}); expected >={minimum} under {dep_root}"
        )
    print(f"[deps] HF hub ok ({hub_ver} @ {hub_file})")


# PyPI on Kaggle has 0.22.2 and 0.23.1 but no stable 0.23.0; transformers 5.5 needs <=0.23.0.
KAGGLE_TOKENIZERS_PIN = "0.22.2"


def _verify_pydeps_tokenizers(dep_root: str, *, exact: str = KAGGLE_TOKENIZERS_PIN) -> None:
    """Keep tokenizers under pydeps and <=0.23.0 so transformers 5.5 import passes."""
    for mod in ("tokenizers", "transformers"):
        _purge_imported_modules(mod)
    _prepend_kaggle_pydeps_hf_stack(dep_root)
    import tokenizers

    ver = tokenizers.__version__
    tok_file = str(getattr(tokenizers, "__file__", "") or "").replace("\\", "/")
    dep_norm = str(Path(dep_root).resolve()).replace("\\", "/")
    if ver != exact or dep_norm not in tok_file:
        raise RuntimeError(
            f"Kaggle tokenizers mismatch: {ver} @ {tok_file}; need =={exact} under {dep_root}"
        )
    print(f"[deps] tokenizers ok ({ver} @ {tok_file})")


def _verify_pydeps_bitsandbytes_package(dep_root: str) -> None:
    """Presence only — do not import here (torch op registration is single-shot per kernel)."""
    bnb_init = Path(dep_root) / "bitsandbytes" / "__init__.py"
    if not bnb_init.is_file():
        raise RuntimeError(f"bitsandbytes not installed under {dep_root}")
    print(f"[deps] bitsandbytes package ok (@ {bnb_init})")


def _import_bitsandbytes_once() -> None:
    """Import pydeps bitsandbytes once per Kaggle session before 4-bit load."""
    if _is_kaggle():
        _prepare_kaggle_import_env()
        dep_root = str(_kaggle_pydeps_root().resolve())
        if not _kaggle_pydeps_bitsandbytes_loaded():
            if "bitsandbytes" in sys.modules:
                _purge_imported_modules("bitsandbytes")
            _prepend_kaggle_pydeps_hf_stack(dep_root)
    import bitsandbytes

    if _is_kaggle():
        print(
            f"[deps] bitsandbytes ok ({bitsandbytes.__version__} @ "
            f"{getattr(bitsandbytes, '__file__', '')})",
            flush=True,
        )


def _verify_system_torch_after_pydeps() -> None:
    """After pip --target: delete stray torch wheels only; never re-import torch (docstring crash)."""
    if not _is_kaggle():
        return
    dep = _kaggle_pydeps_root().resolve()
    if dep.is_dir():
        _strip_pydeps_torch_stack(dep, purge_modules=False)
    if _torch_is_kaggle_system_loaded():
        torch_mod = sys.modules["torch"]
        print(
            f"[deps] verified system torch {torch_mod.__version__} @ {getattr(torch_mod, '__file__', '')} "
            "(kept loaded; no re-import)"
        )
        return
    raise RuntimeError(
        "Kaggle system torch was unloaded during pydeps install (do not purge torch modules). "
        "Session Restart → Cell1 v44+ → Run All."
    )


def _print_kaggle_gpu_banner() -> None:
    torch_mod = sys.modules.get("torch")
    if torch_mod is None:
        _verify_system_torch_after_pydeps()
        torch_mod = sys.modules["torch"]
    if torch_mod.cuda.is_available():
        print(
            f"[GPU] {torch_mod.cuda.get_device_name(0)} "
            f"capability={torch_mod.cuda.get_device_capability(0)}"
        )


def _kaggle_import_training_stack() -> None:
    """Prepend pydeps for HF/trl; system torch must already be loaded from /usr/local."""
    if not _is_kaggle():
        return
    _prepare_kaggle_import_env()
    dep_root = str(_kaggle_pydeps_root().resolve())
    for mod in _HF_STACK_MODULES:
        _purge_imported_modules(mod)
    _prepend_kaggle_pydeps_hf_stack(dep_root)
    _verify_system_torch_after_pydeps()
    _patch_transformers_skip_torchvision()


def _strip_pydeps_torch_stack(dep_root: Path, *, purge_modules: bool = True) -> None:
    removed: list[str] = []
    for entry in sorted(dep_root.iterdir()):
        base = entry.name.split("-")[0].split(".")[0]
        if not any(base == p or entry.name.startswith(p) for p in _PYDEPS_STRIP_PREFIXES):
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)
        removed.append(entry.name)
    if purge_modules and _torch_is_kaggle_system_loaded():
        purge_modules = False
    if purge_modules:
        for prefix in _PYDEPS_STRIP_PREFIXES:
            _purge_imported_modules(prefix)
    if removed:
        print(f"[deps] stripped pydeps torch stack ({len(removed)} entries): {removed[:8]}{'...' if len(removed) > 8 else ''}")


def _hub_version_at_least(version: str, minimum: str) -> bool:
    def _parts(v: str) -> tuple[int, ...]:
        out: list[int] = []
        for piece in version.split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            out.append(int(digits) if digits else 0)
        return tuple(out)

    return _parts(version) >= _parts(minimum)


def _ensure_kaggle_deps() -> None:
    if not _is_kaggle():
        return
    import subprocess

    _prepare_kaggle_import_env()
    _purge_kaggle_torchvision_modules()
    _block_kaggle_torchvision_import()
    cap = _gpu_capability()
    print(f"[deps] kaggle gpu capability={cap}")

    if cap[0] < 7:
        raise RuntimeError(
            "Kaggle scheduled P100/sm_60 — Nemotron 30B needs GPU T4 x2. "
            "Open the notebook → Settings → Accelerator → GPU T4 x2 → Save & Run All. "
            "URL: https://www.kaggle.com/code/familyunion/nemotron-qlora-private-train-v2-notebook-t4"
        )

    _bootstrap_kaggle_torch_isolation()
    _patch_system_transformers_torchvision_probe()

    try:
        import mamba_ssm  # noqa: F401

        print(f"[deps] mamba_ssm already present: {mamba_ssm.__file__}")
    except ImportError:
        _install_mamba_kaggle_wheels()

    # Kaggle system hub ~1.10 (no parse_hf_uri). Install to /kaggle/working/pydeps; never shadow torch.
    kaggle_pydeps = _kaggle_pydeps_root()
    kaggle_pydeps.mkdir(parents=True, exist_ok=True)
    dep_root = str(kaggle_pydeps.resolve())

    _pip_target = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "--no-cache-dir",
        "--upgrade",
        "--target",
        dep_root,
    ]

    subprocess.check_call(
        _pip_target + ["--force-reinstall", "--no-deps", f"tokenizers=={KAGGLE_TOKENIZERS_PIN}"]
    )
    _strip_pydeps_torch_stack(kaggle_pydeps, purge_modules=False)

    _pip_pkgs = [
        "huggingface_hub==1.17.0",
        "transformers==5.5.0",
        "accelerate",
        "peft",
        "datasets==3.6.0",
        "trl",
        "einops",
        "sentencepiece",
    ]
    if _use_unsloth_on_kaggle():
        _pip_pkgs.append("unsloth")
    # --no-deps: avoid pulling torch 2.12 / numpy 2.4 into pydeps (Kaggle keeps system torch 2.10).
    subprocess.check_call(_pip_target + ["--no-deps", *(_pip_pkgs)])
    _strip_pydeps_torch_stack(kaggle_pydeps, purge_modules=False)
    subprocess.check_call(_pip_target + ["bitsandbytes", "--no-deps"])
    _strip_pydeps_torch_stack(kaggle_pydeps, purge_modules=False)

    subprocess.check_call(
        _pip_target + ["--force-reinstall", "--no-deps", "huggingface_hub==1.17.0"]
    )
    _strip_pydeps_torch_stack(kaggle_pydeps, purge_modules=False)
    subprocess.check_call(
        _pip_target + ["--force-reinstall", "--no-deps", f"tokenizers=={KAGGLE_TOKENIZERS_PIN}"]
    )
    _strip_pydeps_torch_stack(kaggle_pydeps, purge_modules=False)
    _verify_pydeps_huggingface_hub(dep_root)
    _verify_pydeps_tokenizers(dep_root)
    _verify_pydeps_bitsandbytes_package(dep_root)
    _verify_system_torch_after_pydeps()

    try:
        _block_kaggle_torchvision_import()
        _kaggle_import_training_stack()
        _patch_transformers_skip_torchvision()
        import transformers as _tf  # noqa: F401

        print(f"[deps] HF stack ok (transformers {_tf.__version__}, profile=nemotron)")
        from trl import SFTConfig, SFTTrainer  # noqa: F401
        from peft import LoraConfig  # noqa: F401

        if _use_unsloth_on_kaggle():
            from unsloth import FastLanguageModel  # noqa: F401

            print("[deps] unsloth + transformers + trl import probe ok")
        else:
            print("[deps] peft + transformers + trl import probe ok (bitsandbytes import deferred)")
        _import_datasets_dataset()
    except Exception as exc:
        raise RuntimeError(f"transformers/trl/peft stack still broken after align: {exc}") from exc
    _verify_mamba_import()


def build_formatting_func(tokenizer):
    def _format(example: dict) -> str:
        user = example.get("prompt") or example.get("instruction") or ""
        ans = example.get("answer") or example.get("output") or ""
        messages = [
            {"role": "user", "content": user},
            {"role": "assistant", "content": _boxed_answer(ans)},
        ]
        try:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        except Exception:
            return f"User: {user}\nAssistant: {_boxed_answer(ans)}"

    return _format


def build_sft_text_dataset(rows: list[dict[str, str]], tokenizer):
    """Single `text` column — avoids TRL mistaking CSV `prompt` for prompt-completion pairs."""
    Dataset = _import_datasets_dataset()

    fmt = build_formatting_func(tokenizer)
    return Dataset.from_list([{"text": fmt(dict(ex))} for ex in rows])


def _patch_trl_skip_model_card() -> None:
    """TRL save hook calls importlib.metadata.version('trl'); pip --target pydeps has no dist-info."""
    patched = False

    def _noop_create_model_card(self, *args, **kwargs):
        return None

    for import_path, attr in (
        ("trl.trainer.sft_trainer", "SFTTrainer"),
        ("trl.trainer.base_trainer", "BaseTrainer"),
    ):
        try:
            import importlib

            mod = importlib.import_module(import_path)
            cls = getattr(mod, attr, None)
            if cls is None or getattr(cls, "_mkm_skip_model_card", False):
                continue
            cls.create_model_card = _noop_create_model_card  # type: ignore[method-assign]
            cls._mkm_skip_model_card = True
            patched = True
        except Exception:
            continue

    if not patched:
        try:
            from trl import SFTTrainer

            if not getattr(SFTTrainer, "_mkm_skip_model_card", False):
                SFTTrainer.create_model_card = _noop_create_model_card  # type: ignore[method-assign]
                SFTTrainer._mkm_skip_model_card = True
        except Exception:
            pass


def _sft_save_strategy(args: argparse.Namespace, max_steps: int) -> str:
    """Smoke / bounded steps: no HF checkpoint (avoids TRL model-card metadata on Kaggle pydeps)."""
    if args.smoke or max_steps > 0:
        return "no"
    return "epoch" if max_steps <= 0 else "steps"


def _load_train_rows(csv_path: Path, limit: int | None) -> list[dict[str, str]]:
    import pandas as pd

    df = pd.read_csv(csv_path)
    for col in ("id", "prompt", "answer"):
        if col not in df.columns:
            raise ValueError(f"train.csv missing column {col!r}: {csv_path}")
    if limit is not None and limit > 0:
        df = df.head(limit)
    return df.to_dict(orient="records")


def pack_submission(adapter_dir: Path, out_zip: Path) -> None:
    if not (adapter_dir / "adapter_config.json").is_file():
        raise FileNotFoundError(f"adapter_config.json missing under {adapter_dir}")
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in sorted(adapter_dir.iterdir()):
            if fp.is_file():
                zf.write(fp, arcname=fp.name)


def _run_train_unsloth(
    args: argparse.Namespace,
    train_csv: Path,
    out_dir: Path,
    rows: list[dict[str, str]],
) -> dict:
    import torch

    _kaggle_import_training_stack()
    Dataset = _import_datasets_dataset()
    from unsloth import FastLanguageModel
    from trl import SFTConfig, SFTTrainer

    _hf_login_if_needed()

    max_steps = args.max_steps if args.max_steps > 0 else -1
    if args.smoke and max_steps <= 0:
        max_steps = args.smoke_steps

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,
        trust_remote_code=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=args.lora_rank * 2,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    ds = build_sft_text_dataset(rows, tokenizer)
    _patch_trl_skip_model_card()

    train_args = SFTConfig(
        output_dir=str(out_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        max_steps=max_steps,
        learning_rate=args.learning_rate,
        bf16=True,
        logging_steps=10,
        save_strategy=_sft_save_strategy(args, max_steps),
        save_steps=max(50, args.smoke_steps),
        max_length=args.max_seq_len,
        packing=False,
        report_to="none",
        dataset_text_field="text",
        completion_only_loss=False,
        assistant_only_loss=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=train_args,
        train_dataset=ds,
        processing_class=tokenizer,
    )
    trainer.train()
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    sub_zip = out_dir.parent / "submission.zip"
    pack_submission(out_dir, sub_zip)

    return {
        "dry_run": False,
        "train_backend": "unsloth",
        "train_csv": str(train_csv),
        "row_count": len(rows),
        "out_dir": str(out_dir),
        "submission_zip": str(sub_zip),
        "base_model": args.base_model,
        "lora_rank": args.lora_rank,
        "max_steps": max_steps,
        "cuda_device": torch.cuda.get_device_name(0),
    }


def run_train(args: argparse.Namespace) -> dict:
    import torch

    workspace = args.workspace_root if args.workspace_root is not None else _workspace_root()
    train_csv = args.train_csv or _default_train_csv(args.slug, workspace)
    out_dir = args.out_dir or _default_out_dir(workspace)
    out_dir.mkdir(parents=True, exist_ok=True)

    limit = args.limit if args.limit > 0 else None
    if args.smoke and (limit is None or limit > args.smoke_rows):
        limit = args.smoke_rows

    rows = _load_train_rows(train_csv, limit)
    if not rows:
        raise ValueError(f"No train rows from {train_csv}")

    if args.dry_run:
        sample = rows[0]
        return {
            "dry_run": True,
            "train_csv": str(train_csv),
            "row_count": len(rows),
            "sample_prompt_chars": len(sample.get("prompt", "")),
            "sample_answer": sample.get("answer", "")[:80],
            "out_dir": str(out_dir),
            "base_model": args.base_model,
            "lora_rank": args.lora_rank,
        }

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for training (use Kaggle GPU notebook).")

    if _use_unsloth_on_kaggle():
        return _run_train_unsloth(args, train_csv, out_dir, rows)

    if _is_kaggle():
        _kaggle_disk_report("train start")
        _prepare_kaggle_import_env()
        _kaggle_import_training_stack()

    Dataset = _import_datasets_dataset()
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    cap = torch.cuda.get_device_capability(0)
    compute_dtype = torch.bfloat16 if cap[0] >= 8 else torch.float16
    use_4bit = _needs_4bit_training(args)
    profile = _kaggle_train_profile() if _is_kaggle() else "local"

    _hf_login_if_needed()
    local_model = _prefetch_hub_model_if_kaggle(args.base_model)
    model_source = str(local_model) if local_model is not None else args.base_model
    load_local_only = local_model is not None

    print(f"[train] loading tokenizer: {model_source}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        model_source,
        trust_remote_code=True,
        local_files_only=load_local_only,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    _kaggle_free_before_model_load()
    _warn_if_nemotron_vram_tight(args)
    print(f"[train] loading model (4bit={use_4bit}, profile={profile})...", flush=True)
    if use_4bit:
        from peft import prepare_model_for_kbit_training

        _import_bitsandbytes_once()
        skip_modules = _bnb_modules_to_not_convert(args.base_model)
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
            llm_int8_skip_modules=skip_modules,
        )
        print(f"[train] bnb4bit llm_int8_skip_modules={skip_modules}", flush=True)
        max_memory = _bnb4bit_gpu_max_memory()
        print(f"[train] bnb4bit max_memory={max_memory} (GPU only, no CPU/disk)", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_source,
            quantization_config=bnb,
            dtype=compute_dtype,
            device_map="auto",
            max_memory=max_memory,
            low_cpu_mem_usage=True,
            local_files_only=load_local_only,
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            dtype=compute_dtype,
            device_map="auto",
            trust_remote_code=True,
        )
    model.gradient_checkpointing_enable()

    lora_cfg = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_rank * 2,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    if use_4bit:
        _apply_nemotron_qlora_runtime_patches(model)
    print("[train] model ready; building dataset", flush=True)

    ds = build_sft_text_dataset(rows, tokenizer)
    _patch_trl_skip_model_card()

    max_steps = args.max_steps if args.max_steps > 0 else -1
    if args.smoke and max_steps <= 0:
        max_steps = args.smoke_steps

    train_args = SFTConfig(
        output_dir=str(out_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        max_steps=max_steps,
        learning_rate=args.learning_rate,
        bf16=cap[0] >= 8,
        fp16=cap[0] < 8,
        logging_steps=10,
        save_strategy=_sft_save_strategy(args, max_steps),
        save_steps=max(50, args.smoke_steps),
        max_length=args.max_seq_len,
        packing=False,
        report_to="none",
        gradient_checkpointing=True,
        dataset_text_field="text",
        completion_only_loss=False,
        assistant_only_loss=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=train_args,
        train_dataset=ds,
        processing_class=tokenizer,
    )
    print(
        f"[train] SFT start (max_steps={max_steps}, rows={len(rows)}, save={train_args.save_strategy})",
        flush=True,
    )
    trainer.train()
    print("[train] SFT done; saving adapter", flush=True)
    trainer.model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    sub_zip = out_dir.parent / "submission.zip"
    pack_submission(out_dir, sub_zip)

    return {
        "dry_run": False,
        "train_backend": "peft_4bit" if use_4bit else "peft_fp16",
        "kaggle_profile": profile,
        "gpu_capability": list(cap),
        "train_csv": str(train_csv),
        "row_count": len(rows),
        "out_dir": str(out_dir),
        "submission_zip": str(sub_zip),
        "base_model": args.base_model,
        "lora_rank": args.lora_rank,
        "max_steps": max_steps,
        "cuda_device": torch.cuda.get_device_name(0),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Nemotron QLoRA train for Kaggle GPU.")
    p.add_argument("--slug", default=DEFAULT_SLUG)
    p.add_argument("--workspace-root", type=Path, default=None)
    p.add_argument("--train-csv", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--base-model", default=DEFAULT_BASE)
    p.add_argument("--lora-rank", type=int, default=16)
    p.add_argument("--limit", type=int, default=0, help="Cap train rows; 0 = all.")
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--max-steps", type=int, default=0, help="0 = use epochs.")
    p.add_argument("--max-seq-len", type=int, default=768)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--learning-rate", type=float, default=2e-4)
    p.add_argument("--smoke", action="store_true", help="Small row cap + short step limit.")
    p.add_argument("--smoke-rows", type=int, default=64)
    p.add_argument("--smoke-steps", type=int, default=20)
    p.add_argument("--dry-run", action="store_true", help="Parse CSV only; no model load.")
    p.add_argument(
        "--out-report-json",
        type=Path,
        default=Path("reports/kaggle_nemotron_kaggle_train_latest.json"),
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.workspace_root is None:
        args.workspace_root = _workspace_root()
    profile = "local"
    if _is_kaggle():
        profile = _apply_kaggle_profile_defaults(args)
        full = os.getenv("MKM_KAGGLE_FULL", "").strip().lower() in ("1", "true", "yes")
        if profile == "fast":
            args.smoke = True
        elif not full:
            args.smoke = True
        elif os.getenv("MKM_KAGGLE_SMOKE", "").strip().lower() in ("1", "true", "yes"):
            args.smoke = True
        _kaggle_disk_report("main start")
        _ensure_kaggle_deps_for_profile(profile)
    if _is_kaggle():
        _print_kaggle_gpu_banner()
    if args.lora_rank > MAX_LORA_RANK:
        print(f"[ERROR] lora-rank must be <= {MAX_LORA_RANK}", file=sys.stderr)
        return 1

    summary = run_train(args)
    root = args.workspace_root
    report_path = args.out_report_json if args.out_report_json.is_absolute() else root / args.out_report_json
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "kaggle_nemotron_kaggle_train_v1",
        "lane": "private_dev_no_mkm_core",
        "is_kaggle_runtime": _is_kaggle(),
        "submit_allowed_by_policy": False,
        "mkm_core_exposed": False,
        **summary,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] report: {report_path}")
    print(f"[SUMMARY] dry_run={summary.get('dry_run')} rows={summary.get('row_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
