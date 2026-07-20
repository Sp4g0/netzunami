import tkinter as tk
from tkinter import ttk
from ..models import Finding, Severity


SEV_COLORS = {
    "CRITICAL": ("#ff4444", "#660000"),
    "HIGH": ("#ff8800", "#663300"),
    "MEDIUM": ("#ffcc00", "#665500"),
    "LOW": ("#66ccff", "#004466"),
    "INFO": ("#888888", "#333333"),
}


class FindingsPanel(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.findings: list[Finding] = []

        header = tk.Label(self, text=" NetSense AI", font=("Segoe UI", 10, "bold"), anchor="w", padx=8, pady=4)
        header.pack(fill=tk.X)

        self.listbox = tk.Listbox(
            self,
            bg="#1a1a1a",
            fg="#d3d7cf",
            selectbackground="#333333",
            font=("Consolas", 10),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.detail_text = tk.Text(
            self,
            bg="#0d0d0d",
            fg="#aaaaaa",
            font=("Consolas", 9),
            height=5,
            relief=tk.FLAT,
            borderwidth=0,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.detail_text.pack(fill=tk.X, pady=(0, 0))

        action_frame = tk.Frame(self, bg="#1a1a1a")
        action_frame.pack(fill=tk.X, pady=2)

        tk.Button(
            action_frame,
            text="Accetta",
            bg="#2d5a27",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            command=self._accept,
        ).pack(side=tk.LEFT, padx=4, pady=2)

        tk.Button(
            action_frame,
            text="Ignora",
            bg="#5a3a27",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            command=self._dismiss,
        ).pack(side=tk.LEFT, padx=4, pady=2)

    def add_finding(self, rule: dict, line: str = ""):
        finding = Finding(
            severity=rule["severity"],
            title=rule["title"],
            detail=rule["detail"],
            suggestion=rule.get("suggestion", ""),
        )
        self.findings.append(finding)
        sev = finding.severity.value
        display = f"[{sev}] {finding.title}"
        color = SEV_COLORS.get(sev, ("#ffffff", "#333333"))[0]
        self.listbox.insert(tk.END, display)
        idx = self.listbox.size() - 1
        self.listbox.itemconfig(idx, fg=color)

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.findings):
            return
        f = self.findings[idx]
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, f"{f.severity.value}: {f.title}\n")
        self.detail_text.insert(tk.END, f"{f.detail}\n")
        if f.suggestion:
            self.detail_text.insert(tk.END, f"→ {f.suggestion}\n")
        self.detail_text.config(state=tk.DISABLED)

    def _accept(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.itemconfig(sel[0], fg="#44aa44")
            self.listbox.selection_clear(0, tk.END)

    def _dismiss(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            if sel[0] < len(self.findings):
                del self.findings[sel[0]]
