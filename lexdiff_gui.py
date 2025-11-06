#!/usr/bin/env python3
"""Tkinter 기반의 새로운 시각화 도구."""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List

from lexdiff import DependencyError, DiffResult, Operation, run_diff


class LexDiffApp:
    """Modernized GUI built from scratch for reviewing diff results."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("lexdiff – DOCX 문장 비교 도구")
        self.root.geometry("1080x680")
        self.root.minsize(960, 600)
        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.out_docx_var = tk.StringVar()
        self.out_csv_var = tk.StringVar()
        self.threshold_var = tk.DoubleVar(value=0.8)
        self.ignore_punct_var = tk.BooleanVar(value=False)
        self.ignore_space_var = tk.BooleanVar(value=False)

        self.operations: List[Operation] = []
        self._row_map: Dict[str, Operation] = {}

        self.status_var = tk.StringVar(value="준비 완료 – 비교할 파일을 선택하세요.")
        self.summary_var = tk.StringVar(value="")

        self._build_layout()

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        paned = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(paned, padding=12)
        results = ttk.Frame(paned, padding=12)
        paned.add(controls, weight=1)
        paned.add(results, weight=2)

        self._build_controls(controls)
        self._build_results(results)

        status_bar = ttk.Frame(container)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Label(status_bar, textvariable=self.status_var, anchor="w").pack(fill=tk.X, padx=12, pady=6)

    def _build_controls(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        padding = {"padx": (0, 8), "pady": 6}

        self._add_file_row(frame, "원본 DOCX", self.source_var, self._choose_source, row=0, **padding)
        self._add_file_row(frame, "수정 DOCX", self.target_var, self._choose_target, row=1, **padding)
        self._add_file_row(frame, "결과 DOCX", self.out_docx_var, self._choose_out_docx, row=2, **padding)
        self._add_file_row(frame, "결과 CSV", self.out_csv_var, self._choose_out_csv, row=3, **padding)

        options = ttk.LabelFrame(frame, text="옵션", padding=12)
        options.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        options.columnconfigure(1, weight=1)

        ttk.Checkbutton(options, text="구두점 무시", variable=self.ignore_punct_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="공백 무시", variable=self.ignore_space_var).grid(row=0, column=1, sticky="w")

        ttk.Label(options, text="유사도 임계값").grid(row=1, column=0, sticky="w", pady=(12, 0))
        scale = ttk.Scale(
            options,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.threshold_var,
            command=lambda _=None: self._update_threshold_label(),
        )
        scale.grid(row=1, column=1, sticky="ew", pady=(12, 0), padx=(12, 0))
        options.columnconfigure(1, weight=1)

        self.threshold_label = ttk.Label(options, text="0.80")
        self.threshold_label.grid(row=1, column=2, sticky="w", padx=(12, 0))

        self.run_button = ttk.Button(frame, text="비교 실행", command=self._on_run_clicked)
        self.run_button.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(18, 0))

        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 0))

    def _build_results(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        ttk.Label(frame, text="비교 요약", font=("", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.summary_var, foreground="#616161").grid(row=1, column=0, sticky="w", pady=(0, 6))

        columns = ("type", "sim", "original", "revised", "idxA", "idxB")
        self.result_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "type": "유형",
            "sim": "유사도",
            "original": "원본 문장",
            "revised": "수정 문장",
            "idxA": "A#",
            "idxB": "B#",
        }
        widths = {"type": 70, "sim": 80, "original": 260, "revised": 260, "idxA": 60, "idxB": 60}
        for column, text in headings.items():
            self.result_tree.heading(column, text=text)
            self.result_tree.column(column, width=widths[column], anchor=tk.W if column in {"original", "revised"} else tk.CENTER)

        self.result_tree.tag_configure("add", foreground="#1b5e20")
        self.result_tree.tag_configure("del", foreground="#b71c1c")
        self.result_tree.tag_configure("replace", foreground="#f57f17")

        tree_scroll_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        tree_scroll_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.result_tree.grid(row=2, column=0, sticky="nsew")
        tree_scroll_y.grid(row=2, column=1, sticky="ns")
        tree_scroll_x.grid(row=3, column=0, sticky="ew")

        detail_frame = ttk.Frame(frame)
        detail_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.columnconfigure(1, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        ttk.Label(detail_frame, text="원본 문장").grid(row=0, column=0, sticky="w")
        ttk.Label(detail_frame, text="수정 문장").grid(row=0, column=1, sticky="w")

        self.original_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.revised_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.original_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.revised_text.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_selected)

    # ---------------------------------------------------------------- events
    def _add_file_row(self, frame: ttk.Frame, label: str, variable: tk.StringVar, command, row: int, **padding) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **padding)
        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", **padding)
        ttk.Button(frame, text="찾기", command=command).grid(row=row, column=2, sticky="ew", **padding)

    def _choose_source(self) -> None:
        path = filedialog.askopenfilename(title="원본 DOCX 선택", filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")])
        if path:
            self.source_var.set(path)
            self._suggest_outputs()

    def _choose_target(self) -> None:
        path = filedialog.askopenfilename(title="수정 DOCX 선택", filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")])
        if path:
            self.target_var.set(path)
            self._suggest_outputs()

    def _choose_out_docx(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".docx", title="결과 DOCX 저장")
        if path:
            self.out_docx_var.set(path)

    def _choose_out_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", title="결과 CSV 저장")
        if path:
            self.out_csv_var.set(path)

    def _suggest_outputs(self) -> None:
        target = Path(self.target_var.get())
        if not target.exists():
            return
        base = target.stem
        directory = target.parent
        if not self.out_docx_var.get():
            self.out_docx_var.set(str(directory / f"{base}_highlight.docx"))
        if not self.out_csv_var.get():
            self.out_csv_var.set(str(directory / f"{base}_diff.csv"))

    def _update_threshold_label(self) -> None:
        self.threshold_label.config(text=f"{self.threshold_var.get():.2f}")

    def _on_run_clicked(self) -> None:
        errors = self._validate_inputs()
        if errors:
            messagebox.showerror("입력 오류", "\n".join(errors))
            return

        ignore_tokens: List[str] = []
        if self.ignore_punct_var.get():
            ignore_tokens.append("punct")
        if self.ignore_space_var.get():
            ignore_tokens.append("space")

        args = dict(
            source=self.source_var.get(),
            target=self.target_var.get(),
            out_docx=self.out_docx_var.get(),
            out_csv=self.out_csv_var.get(),
            ignore_tokens=ignore_tokens,
            threshold=self.threshold_var.get(),
        )

        self._set_running_state(True)
        self.status_var.set("비교 작업 실행 중…")
        self.progress.config(mode="indeterminate")
        self.progress.start(12)
        self._clear_results()

        thread = threading.Thread(target=self._run_worker, args=(args,), daemon=True)
        thread.start()

    def _run_worker(self, args: dict) -> None:
        try:
            result = run_diff(**args)
        except DependencyError as exc:
            self.root.after(0, self._handle_failure, exc)
            return
        except Exception as exc:  # pragma: no cover - surfaced via UI
            self.root.after(0, self._handle_failure, exc)
            return
        self.root.after(0, self._handle_success, result)

    def _handle_success(self, result: DiffResult) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=100)
        self._set_running_state(False)
        self.operations = result.operations
        self._populate_rows(result)
        changed = any(row.type != "equal" for row in result.rows)
        if changed:
            self.status_var.set("완료 – 변경된 문장을 미리보기에서 확인하세요.")
        else:
            self.status_var.set("완료 – 변경 사항이 없습니다.")
        messagebox.showinfo("완료", "비교가 종료되었습니다. 결과 파일을 확인하세요.")

    def _handle_failure(self, exc: Exception) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self._set_running_state(False)
        self.status_var.set("실패 – 상세 메시지를 확인하세요.")
        self._clear_results()
        messagebox.showerror("실패", f"비교 중 오류가 발생했습니다:\n{exc}")

    def _set_running_state(self, running: bool) -> None:
        self.run_button.config(state=tk.DISABLED if running else tk.NORMAL)

    def _validate_inputs(self) -> List[str]:
        errors: List[str] = []
        if not self.source_var.get():
            errors.append("원본 DOCX 파일을 선택하세요.")
        if not self.target_var.get():
            errors.append("수정 DOCX 파일을 선택하세요.")
        if not self.out_docx_var.get():
            errors.append("결과 DOCX 저장 위치를 지정하세요.")
        if not self.out_csv_var.get():
            errors.append("CSV 저장 위치를 지정하세요.")
        threshold = self.threshold_var.get()
        if not 0.0 <= threshold <= 1.0:
            errors.append("임계값은 0과 1 사이여야 합니다.")
        return errors

    # -------------------------------------------------------------- results
    def _clear_results(self) -> None:
        self.operations = []
        self._row_map.clear()
        self.summary_var.set("")
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self._set_text(self.original_text, "")
        self._set_text(self.revised_text, "")

    def _populate_rows(self, result: DiffResult) -> None:
        counts = {"add": 0, "del": 0, "replace": 0}
        for row in result.rows:
            if row.type in counts:
                counts[row.type] += 1
        summary = ", ".join(f"{kind}: {count}" for kind, count in counts.items()) or "변경 없음"
        self.summary_var.set(summary)

        if not result.rows:
            return

        for op in result.operations:
            if op.kind == "equal":
                continue
            tree_row = self.result_tree.insert(
                "",
                tk.END,
                values=(
                    op.kind,
                    f"{op.similarity:.2f}" if op.kind == "replace" else "",
                    self._truncate(op.original.text if op.original else ""),
                    self._truncate(op.revised.text if op.revised else ""),
                    str(op.original.index + 1) if op.original else "",
                    str(op.revised.index + 1) if op.revised else "",
                ),
                tags=(op.kind,),
            )
            self._row_map[tree_row] = op

        first = self.result_tree.get_children()
        if first:
            self.result_tree.selection_set(first[0])
            self.result_tree.focus(first[0])
            self._on_result_selected()

    def _on_result_selected(self, event=None) -> None:  # noqa: ARG002 - tkinter callback
        selected = self.result_tree.selection()
        if not selected:
            self._set_text(self.original_text, "")
            self._set_text(self.revised_text, "")
            return
        op = self._row_map.get(selected[0])
        if not op:
            return
        original = self._compose_sentence(op.original)
        revised = self._compose_sentence(op.revised)
        self._set_text(self.original_text, original or "(없음)")
        self._set_text(self.revised_text, revised or "(없음)")

    # ------------------------------------------------------------- helpers
    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.config(state=tk.DISABLED)

    def _compose_sentence(self, record) -> str:
        if not record:
            return ""
        prefix = record.prefix or ""
        postfix = record.postfix or ""
        return f"{prefix}{record.text}{postfix}".strip() or record.text

    @staticmethod
    def _truncate(text: str, limit: int = 100) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - environment specific
        message = (
            "그래픽 디스플레이를 찾을 수 없어 GUI를 실행할 수 없습니다.\n"
            "Codespaces 같은 터미널 환경에서는 CLI(`python lexdiff.py …`) 또는 "
            "웹 인터페이스(`python lexdiff_web.py`)를 사용해 주세요."
        )
        print(message, file=sys.stderr)
        raise SystemExit(1) from exc

    LexDiffApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - direct invocation only
    main()
