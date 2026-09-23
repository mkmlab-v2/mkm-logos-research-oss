"""Windows tray UI for MKM Secure Agent Runtime V0.5.

This UI is a local human surface. It does not expose an MCP approval tool.
"""
from __future__ import annotations

import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw
import pystray

from approval import ApprovalBroker, ApprovalError
from ollama_manager import OllamaManager, OllamaManagerError
from tray_controller import ApprovalView, TrayController


POLL_MS = 1000


def _roots() -> list[Path]:
    raw = os.environ.get("MKM_AGENT_ROOTS", "")
    roots = [Path(x) for x in raw.split(os.pathsep) if x.strip()]
    if not roots:
        raise RuntimeError("MKM_AGENT_ROOTS is required")
    return roots


def _state_dir() -> Path:
    raw = os.environ.get("MKM_AGENT_STATE", "").strip()
    if not raw:
        raise RuntimeError("MKM_AGENT_STATE is required")
    return Path(raw)


def _icon_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((8, 8, 56, 56), outline="black", width=5)
    draw.line((20, 43, 31, 20, 43, 43), fill="black", width=5)
    return img


class ApprovalWindow:
    def __init__(self, root: tk.Tk, controller: TrayController):
        self.root = root
        self.controller = controller
        self.window = tk.Toplevel(root)
        self.window.title("MKM Agent Approvals")
        self.window.geometry("820x420")
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)

        self.tree = ttk.Treeview(
            self.window,
            columns=("action", "target", "expires"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("action", text="Action")
        self.tree.heading("target", text="Target")
        self.tree.heading("expires", text="Expires")
        self.tree.column("action", width=130)
        self.tree.column("target", width=480)
        self.tree.column("expires", width=170)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        detail_frame = ttk.Frame(self.window)
        detail_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.detail = tk.StringVar(value="Select an approval request.")
        ttk.Label(
            detail_frame,
            textvariable=self.detail,
            wraplength=780,
            justify="left",
        ).pack(fill="x")

        buttons = ttk.Frame(self.window)
        buttons.pack(fill="x", padx=8, pady=(0, 10))
        ttk.Button(buttons, text="Approve once", command=self._approve).pack(side="left")
        ttk.Button(buttons, text="Deny", command=self._deny).pack(side="left", padx=8)
        ttk.Button(buttons, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(buttons, text="Hide", command=self.window.withdraw).pack(side="right")
        self.tree.bind("<<TreeviewSelect>>", self._show_detail)
        self._rows: dict[str, ApprovalView] = {}
        self.window.withdraw()

    def show(self) -> None:
        self.refresh()
        self.window.deiconify()
        self.window.lift()
        self.window.attributes("-topmost", True)
        self.window.after(250, lambda: self.window.attributes("-topmost", False))

    def refresh(self) -> None:
        rows = self.controller.pending()
        self._rows = {x.approval_id: x for x in rows}
        existing = set(self.tree.get_children())
        wanted = set(self._rows)
        for iid in existing - wanted:
            self.tree.delete(iid)
        for row in rows:
            values = (row.action, row.target, row.expires_at)
            if row.approval_id in existing:
                self.tree.item(row.approval_id, values=values)
            else:
                self.tree.insert("", "end", iid=row.approval_id, values=values)
        if not rows:
            self.detail.set("No pending approvals.")

    def _selected(self) -> ApprovalView | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._rows.get(selection[0])

    def _show_detail(self, _event=None) -> None:
        row = self._selected()
        if row is None:
            return
        self.detail.set(
            f"ID: {row.approval_id}\n"
            f"Action: {row.action}\n"
            f"Target: {row.target}\n"
            f"Argument digest: {row.args_sha256}\n"
            f"Created: {row.created_at}\n"
            f"Expires: {row.expires_at}"
        )

    def _approve(self) -> None:
        row = self._selected()
        if row is None:
            messagebox.showinfo("MKM Agent", "Select a request first.", parent=self.window)
            return
        try:
            self.controller.approve(row.approval_id)
        except ApprovalError as exc:
            messagebox.showerror("MKM Agent", str(exc), parent=self.window)
        self.refresh()

    def _deny(self) -> None:
        row = self._selected()
        if row is None:
            messagebox.showinfo("MKM Agent", "Select a request first.", parent=self.window)
            return
        try:
            self.controller.deny(row.approval_id)
        except ApprovalError as exc:
            messagebox.showerror("MKM Agent", str(exc), parent=self.window)
        self.refresh()


class MKMTrayApp:
    def __init__(self):
        roots = _roots()
        state = _state_dir()
        broker = ApprovalBroker(state, protected_roots=roots)
        ollama = OllamaManager(
            os.environ.get("MKM_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        )

        self.root = tk.Tk()
        self.root.withdraw()
        self.controller = TrayController(
            broker,
            ollama,
            on_new_approval=self._on_new_approval,
        )
        self.approvals = ApprovalWindow(self.root, self.controller)
        self.status_var = tk.StringVar(value="Starting")
        self.status_window: tk.Toplevel | None = None

        self.icon = pystray.Icon(
            "mkm-secure-agent",
            _icon_image(),
            "MKM Secure Agent",
            menu=pystray.Menu(
                pystray.MenuItem("Approvals", lambda: self._ui(self.approvals.show)),
                pystray.MenuItem("Status", lambda: self._ui(self.show_status)),
                pystray.MenuItem("Start / check Ollama", lambda: self._ui(self.ensure_ollama)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda: self._ui(self.quit)),
            ),
        )

    def _ui(self, fn) -> None:
        self.root.after(0, fn)

    def _on_new_approval(self, item: ApprovalView) -> None:
        self.root.after(0, self.approvals.show)
        try:
            self.icon.notify(
                f"{item.action}\n{item.target}",
                "MKM approval required",
            )
        except Exception:
            pass

    def _poll(self) -> None:
        try:
            self.controller.poll()
        finally:
            self.root.after(POLL_MS, self._poll)

    def _ollama_background(self) -> None:
        try:
            status = self.controller.ensure_ollama()
            message = (
                f"Ollama: HEALTHY\nEndpoint: {status.endpoint}\n"
                f"Models: {status.model_count}\nPID: {status.pid or '-'}"
            )
        except Exception as exc:
            message = f"Ollama unavailable: {exc}"
        self.root.after(0, lambda: self.status_var.set(message))

    def ensure_ollama(self) -> None:
        self.status_var.set("Checking / starting local Ollama...")
        self.show_status()
        threading.Thread(target=self._ollama_background, daemon=True).start()

    def show_status(self) -> None:
        status = self.controller.ollama_status()
        self.status_var.set(
            f"Runtime: local stdio candidate\n"
            f"Pending approvals: {len(self.controller.pending())}\n"
            f"Ollama: {'HEALTHY' if status.available else 'OFFLINE'}\n"
            f"Endpoint: {status.endpoint}\n"
            f"Executable: {status.executable or 'not found'}\n"
            f"Started by MKM: {status.started_by_runtime}"
        )
        if self.status_window is None or not self.status_window.winfo_exists():
            self.status_window = tk.Toplevel(self.root)
            self.status_window.title("MKM Secure Agent Status")
            self.status_window.geometry("600x260")
            ttk.Label(
                self.status_window,
                textvariable=self.status_var,
                justify="left",
                wraplength=560,
            ).pack(fill="both", expand=True, padx=16, pady=16)
            ttk.Button(
                self.status_window,
                text="Start / check Ollama",
                command=self.ensure_ollama,
            ).pack(pady=(0, 16))
        else:
            self.status_window.deiconify()
            self.status_window.lift()

    def run(self) -> None:
        self.icon.run_detached()
        self.root.after(POLL_MS, self._poll)
        # Auto-connect is local-only and forced to 127.0.0.1.
        if os.environ.get("MKM_OLLAMA_AUTOSTART", "1") == "1":
            threading.Thread(target=self._ollama_background, daemon=True).start()
        self.root.mainloop()

    def quit(self) -> None:
        self.controller.shutdown()
        try:
            self.icon.stop()
        finally:
            self.root.quit()


def main() -> None:
    if os.name != "nt":
        raise SystemExit("V0.5 tray shell currently supports Windows only")
    MKMTrayApp().run()


if __name__ == "__main__":
    main()
