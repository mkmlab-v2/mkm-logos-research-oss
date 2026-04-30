from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

try:
    import torch

    _TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None
    _TORCH_AVAILABLE = False


def _require_torch() -> None:
    if not _TORCH_AVAILABLE:
        raise RuntimeError("PyTorch is required for LogosEncoder.")


def _device_or_cpu(device: str | None) -> str:
    if device == "cuda" and _TORCH_AVAILABLE and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _text_to_vec4(text: str) -> list[float]:
    # Deterministic 4D projection for branch-local reproducibility.
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals = [int.from_bytes(digest[i * 8 : (i + 1) * 8], "big") for i in range(4)]
    vec = [((v % 1_000_000) / 1_000_000.0) for v in vals]
    s = sum(vec) or 1.0
    return [v / s for v in vec]


class LogosEncoder:
    def __init__(self) -> None:
        _require_torch()
        self._eval = False

    def eval(self) -> "LogosEncoder":
        self._eval = True
        return self

    def encode_texts_batch_to_logos_embeddings(
        self, texts: Sequence[str], device: str | None = None
    ) -> "torch.Tensor":
        _require_torch()
        dev = _device_or_cpu(device)
        rows = [_text_to_vec4(str(t or "")) for t in texts]
        if not rows:
            return torch.zeros((0, 4), dtype=torch.float32, device=dev)
        t = torch.tensor(rows, dtype=torch.float32, device=dev)
        denom = torch.norm(t, dim=1, keepdim=True).clamp(min=1e-8)
        return t / denom

    def encode_text_to_logos_embedding(
        self, text: str, device: str | None = None
    ) -> "torch.Tensor":
        return self.encode_texts_batch_to_logos_embeddings([text], device=device)


def nearest_logos_neighbors(
    query_vec: "torch.Tensor", corpus: "torch.Tensor", k: int = 5
) -> tuple["torch.Tensor", "torch.Tensor"]:
    _require_torch()
    if corpus.numel() == 0:
        return (
            torch.zeros((0,), dtype=torch.float32),
            torch.zeros((0,), dtype=torch.long),
        )
    q = query_vec.float()
    if q.ndim == 2:
        q = q.squeeze(0)
    q = q / (torch.norm(q) + 1e-8)
    c = corpus.float()
    c = c / torch.norm(c, dim=1, keepdim=True).clamp(min=1e-8)
    sims = torch.mv(c, q)
    kk = max(1, min(int(k), sims.shape[0]))
    vals, idx = torch.topk(sims, k=kk, largest=True, sorted=True)
    return vals, idx


def calculate_resonance(market_vec: "torch.Tensor", logos_vec: "torch.Tensor") -> "torch.Tensor":
    _require_torch()
    m = market_vec.float()
    l = logos_vec.float()
    if m.ndim == 1:
        m = m.unsqueeze(0)
    if l.ndim == 1:
        l = l.unsqueeze(0)
    m = m / torch.norm(m, dim=1, keepdim=True).clamp(min=1e-8)
    l = l / torch.norm(l, dim=1, keepdim=True).clamp(min=1e-8)
    return (m * l).sum(dim=1, keepdim=True)


@dataclass(frozen=True)
class ResonanceRiskAdjustment:
    adjusted_cap: float
    resonance: float
    delta: float


def apply_logos_resonance_to_risk_cap(
    base_cap: float,
    resonance: float,
    risk_multiplier_min: float,
    risk_multiplier_max: float,
    strength: float = 0.12,
) -> ResonanceRiskAdjustment:
    # resonance in [-1,1] nudges cap, then clips into policy band.
    delta = float(strength) * float(max(-1.0, min(1.0, resonance)))
    adjusted = float(base_cap) + delta
    adjusted = max(float(risk_multiplier_min), min(float(risk_multiplier_max), adjusted))
    return ResonanceRiskAdjustment(adjusted_cap=adjusted, resonance=float(resonance), delta=delta)


_GLOBAL_ENCODER: LogosEncoder | None = None


def get_logos_encoder() -> LogosEncoder:
    global _GLOBAL_ENCODER
    if _GLOBAL_ENCODER is None:
        _GLOBAL_ENCODER = LogosEncoder().eval()
    return _GLOBAL_ENCODER
