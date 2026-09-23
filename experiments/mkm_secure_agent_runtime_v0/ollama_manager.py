"""Local Ollama lifecycle helper for MKM Secure Agent Runtime V0.5."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class OllamaManagerError(RuntimeError):
    pass


@dataclass(frozen=True)
class OllamaStatus:
    available: bool
    endpoint: str
    executable: str | None
    started_by_runtime: bool
    pid: int | None
    model_count: int | None
    detail: str


def _validate_loopback_url(base_url: str) -> str:
    value = base_url.rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "http":
        raise OllamaManagerError("V0.5 Ollama auto-connect requires http loopback URL")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise OllamaManagerError("Ollama endpoint must be loopback-only")
    if parsed.port not in {None, 11434}:
        raise OllamaManagerError("V0.5 Ollama auto-connect allows port 11434 only")
    return value


def find_ollama_executable() -> Path | None:
    hit = shutil.which("ollama")
    if hit:
        return Path(hit).resolve()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return candidate.resolve()
    return None


class OllamaManager:
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = _validate_loopback_url(base_url)
        self._process: subprocess.Popen[str] | None = None
        self._started_by_runtime = False

    def _health_payload(self, timeout: float = 1.0) -> dict[str, Any]:
        req = Request(self.base_url + "/api/tags", method="GET")
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise OllamaManagerError(f"Ollama health HTTP {resp.status}")
            return json.loads(resp.read().decode("utf-8"))

    def is_healthy(self, timeout: float = 1.0) -> bool:
        try:
            self._health_payload(timeout=timeout)
            return True
        except Exception:
            return False

    def status(self) -> OllamaStatus:
        exe = find_ollama_executable()
        try:
            payload = self._health_payload(timeout=1.0)
            models = payload.get("models")
            count = len(models) if isinstance(models, list) else None
            return OllamaStatus(
                available=True,
                endpoint=self.base_url,
                executable=str(exe) if exe else None,
                started_by_runtime=self._started_by_runtime,
                pid=self._process.pid if self._process and self._process.poll() is None else None,
                model_count=count,
                detail="HEALTHY",
            )
        except Exception as exc:
            return OllamaStatus(
                available=False,
                endpoint=self.base_url,
                executable=str(exe) if exe else None,
                started_by_runtime=self._started_by_runtime,
                pid=self._process.pid if self._process and self._process.poll() is None else None,
                model_count=None,
                detail=f"UNAVAILABLE:{type(exc).__name__}",
            )

    def ensure_running(self, *, wait_seconds: float = 20.0) -> OllamaStatus:
        if self.is_healthy(timeout=1.0):
            return self.status()

        exe = find_ollama_executable()
        if exe is None:
            raise OllamaManagerError("ollama executable not found")

        if self._process is not None and self._process.poll() is None:
            # A process we started exists but health is still unavailable.
            return self._wait_for_health(wait_seconds)

        env = dict(os.environ)
        # Force loopback-only listener even if the parent environment differs.
        env["OLLAMA_HOST"] = "127.0.0.1:11434"
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self._process = subprocess.Popen(
            [str(exe), "serve"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
            creationflags=creationflags,
        )
        self._started_by_runtime = True
        try:
            return self._wait_for_health(wait_seconds)
        except Exception:
            # Fail closed: never leave a process we started behind after
            # auto-connect failure.
            self.stop_if_started()
            raise

    def _wait_for_health(self, wait_seconds: float) -> OllamaStatus:
        deadline = time.monotonic() + max(0.0, wait_seconds)
        while time.monotonic() <= deadline:
            if self.is_healthy(timeout=0.75):
                return self.status()
            if self._process is not None and self._process.poll() is not None:
                raise OllamaManagerError(
                    f"ollama serve exited early with code {self._process.returncode}"
                )
            time.sleep(0.2)
        raise OllamaManagerError("Ollama did not become healthy before timeout")

    def stop_if_started(self, *, timeout: float = 3.0) -> bool:
        proc = self._process
        if not self._started_by_runtime or proc is None or proc.poll() is not None:
            return False
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=timeout)
        return True
