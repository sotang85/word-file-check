#!/usr/bin/env python3
"""Simple Tkinter front-end for the lexdiff CLI."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List

from lexdiff import run_diff


class LexDiffGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("lexdiff – DOCX Diff Viewer")
        self.root.geometry("960x640")

        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.out_docx_var = tk.StringVar()
        self.out_csv_var = tk.StringVar()
        self.threshold_var = tk.DoubleVar(value=0.8)
        self.ignore_punct_var = tk.BooleanVar(value=False)
        self.ignore_space_var = tk.BooleanVar(value=False)

        self.operations: List[dict] = []
        self._result_rows: Dict[str, dict] = {}

        self._build_layout()

    def _build_layout(self) -> None:
        padding = {"padx": 12, "pady": 8}
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Source document selection
        self._add_file_picker(main, "원본 DOCX", self.source_var, self._choose_source, row=0, **padding)
        self._add_file_picker(main, "수정 DOCX", self.target_var, self._choose_target, row=1, **padding)
        self._add_file_picker(main, "결과 DOCX", self.out_docx_var, self._choose_out_docx, row=2, **padding)
        self._add_file_picker(main, "Diff CSV", self.out_csv_var, self._choose_out_csv, row=3, **padding)

        # Options section
        options_frame = ttk.LabelFrame(main, text="옵션")
        options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", **padding)

        ttk.Checkbutton(options_frame, text="구두점 무시", variable=self.ignore_punct_var).grid(
            row=0, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(options_frame, text="공백 무시", variable=self.ignore_space_var).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )

        ttk.Label(options_frame, text="유사도 임계값").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        scale = ttk.Scale(
            options_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.threshold_var,
            command=lambda _: self._update_threshold_label(),
        )
        scale.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        options_frame.columnconfigure(1, weight=1)

        self.threshold_label = ttk.Label(options_frame, text="0.80")
        self.threshold_label.grid(row=1, column=2, sticky="w", padx=8, pady=4)

        # Result preview
        results_frame = ttk.LabelFrame(main, text="결과 미리보기")
        results_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", **padding)
        main.rowconfigure(5, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        results_frame.rowconfigure(2, weight=1)

        columns = ("type", "sim", "original", "revised", "idxA", "idxB")
        self.result_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.result_tree.heading("type", text="유형")
        self.result_tree.heading("sim", text="유사도")
        self.result_tree.heading("original", text="원본")
        self.result_tree.heading("revised", text="수정")
        self.result_tree.heading("idxA", text="A#")
        self.result_tree.heading("idxB", text="B#")
        self.result_tree.column("type", width=70, anchor="center")
        self.result_tree.column("sim", width=80, anchor="center")
        self.result_tree.column("original", width=260, anchor="w")
        self.result_tree.column("revised", width=260, anchor="w")
        self.result_tree.column("idxA", width=60, anchor="center")
        self.result_tree.column("idxB", width=60, anchor="center")

        self.result_tree.tag_configure("add", foreground="#1b5e20")
        self.result_tree.tag_configure("del", foreground="#b71c1c")
        self.result_tree.tag_configure("replace", foreground="#f57f17")

        tree_scroll_y = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        tree_scroll_x = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.result_tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))
        tree_scroll_y.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        tree_scroll_x.grid(row=1, column=0, sticky="ew", padx=8)

        detail_frame = ttk.Frame(results_frame)
        detail_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.columnconfigure(1, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        ttk.Label(detail_frame, text="원본 문장").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Label(detail_frame, text="수정 문장").grid(row=0, column=1, sticky="w", padx=(4, 0))

        self.original_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.revised_text = tk.Text(detail_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.original_text.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        self.revised_text.grid(row=1, column=1, sticky="nsew", padx=(4, 0))

        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_selected)

        # Status and actions
        self.status_var = tk.StringVar(value="준비 완료")
        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", **padding)

        ttk.Label(main, textvariable=self.status_var).grid(row=7, column=0, columnspan=3, sticky="w", **padding)

        self.run_button = ttk.Button(main, text="비교 실행", command=self._on_run_clicked)
        self.run_button.grid(row=8, column=0, columnspan=3, sticky="ew", **padding)

        for col in range(3):
            main.columnconfigure(col, weight=1)

        self._update_threshold_label()

    def _add_file_picker(
        self,
        container: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        command,
        row: int,
        **padding,
    ) -> None:
        ttk.Label(container, text=label).grid(row=row, column=0, sticky="w", **padding)
        entry = ttk.Entry(container, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", **padding)
        ttk.Button(container, text="찾기", command=command).grid(row=row, column=2, sticky="ew", **padding)

    def _choose_source(self) -> None:
        path = filedialog.askopenfilename(
            title="원본 DOCX 선택",
            filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")],
        )
        if path:
            self.source_var.set(path)
            self._suggest_outputs()

    def _choose_target(self) -> None:
        path = filedialog.askopenfilename(
            title="수정 DOCX 선택",
            filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")],
        )
        if path:
            self.target_var.set(path)
            self._suggest_outputs()

    def _choose_out_docx(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            title="하이라이트 DOCX 저장",
            filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")],
        )
        if path:
            self.out_docx_var.set(path)

    def _choose_out_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            title="Diff CSV 저장",
            filetypes=[("CSV", "*.csv"), ("모든 파일", "*.*")],
        )
        if path:
            self.out_csv_var.set(path)

    def _suggest_outputs(self) -> None:
        target = Path(self.target_var.get())
        if target.exists():
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

        self._set_running(True)
        self.status_var.set("비교 작업을 실행 중...")
        self.progress.config(mode="indeterminate")
        self.progress.start(10)
        self._clear_results()

        args = dict(
            source=self.source_var.get(),
            target=self.target_var.get(),
            out_docx=self.out_docx_var.get(),
            out_csv=self.out_csv_var.get(),
            ignore_tokens=ignore_tokens,
            threshold=self.threshold_var.get(),
        )

        thread = threading.Thread(target=self._run_diff_thread, args=(args,), daemon=True)
        thread.start()

    def _run_diff_thread(self, args: dict) -> None:
        try:
            operations = run_diff(**args)
        except Exception as exc:  # pragma: no cover - surfaced in UI
            self.root.after(0, self._handle_failure, exc)
            return
        self.root.after(0, self._handle_success, operations)

    def _handle_success(self, operations: List[dict]) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=100)
        self._populate_results(operations)
        if any(op.get("type") != "equal" for op in operations):
            self.status_var.set("완료! 하단 미리보기에서 변경 사항을 확인하세요.")
            message = "비교 작업이 끝났습니다. 결과 파일과 미리보기를 확인하세요."
        else:
            self.status_var.set("완료! 변경 사항이 없습니다.")
            message = "비교 작업이 끝났습니다. 변경 사항이 발견되지 않았습니다."
        self._set_running(False)
        messagebox.showinfo("완료", message)

    def _handle_failure(self, exc: Exception) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self.status_var.set("실패: 자세한 오류 메시지를 확인하세요.")
        self._set_running(False)
        self._clear_results()
        messagebox.showerror("실패", f"비교 작업 중 오류가 발생했습니다:\n{exc}")

    def _set_running(self, running: bool) -> None:
        self.run_button.config(state=tk.DISABLED if running else tk.NORMAL)

    def _validate_inputs(self) -> List[str]:
        errors: List[str] = []
        if not self.source_var.get():
            errors.append("원본 DOCX 파일을 선택하세요.")
        if not self.target_var.get():
            errors.append("수정 DOCX 파일을 선택하세요.")
        if not self.out_docx_var.get():
            errors.append("결과 DOCX 저장 위치를 선택하세요.")
        if not self.out_csv_var.get():
            errors.append("CSV 저장 위치를 선택하세요.")

        threshold = self.threshold_var.get()
        if not 0.0 <= threshold <= 1.0:
            errors.append("임계값은 0과 1 사이여야 합니다.")
        return errors

    def _clear_results(self) -> None:
        self.operations = []
        self._result_rows.clear()
        if hasattr(self, "result_tree"):
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
        self._set_text(self.original_text, "")
        self._set_text(self.revised_text, "")

    def _populate_results(self, operations: List[dict]) -> None:
        self.operations = operations
        self._result_rows.clear()
        filtered = [op for op in operations if op.get("type") != "equal"]
        if not filtered:
            return

        for op in filtered:
            item_id = self.result_tree.insert(
                "",
                tk.END,
                values=(
                    op.get("type", ""),
                    f"{op.get('sim', 0.0):.2f}" if op.get("type") == "replace" else "",
                    self._truncate(self._record_text(op.get("a"))),
                    self._truncate(self._record_text(op.get("b"))),
                    self._record_index(op.get("a")),
                    self._record_index(op.get("b")),
                ),
                tags=(op.get("type", ""),),
            )
            self._result_rows[item_id] = op

        first = self.result_tree.get_children()
        if first:
            self.result_tree.selection_set(first[0])
            self.result_tree.focus(first[0])
            self._on_result_selected()

    def _on_result_selected(self, event=None) -> None:
        selected = self.result_tree.selection()
        if not selected:
            self._set_text(self.original_text, "")
            self._set_text(self.revised_text, "")
            return
        op = self._result_rows.get(selected[0])
        if not op:
            return
        original = self._record_full_text(op.get("a"))
        revised = self._record_full_text(op.get("b"))
        self._set_text(self.original_text, original)
        self._set_text(self.revised_text, revised)

    def _record_text(self, record) -> str:
        if not record:
            return ""
        return record.text

    def _record_full_text(self, record) -> str:
        if not record:
            return "(없음)"
        prefix = record.prefix or ""
        postfix = record.postfix or ""
        return f"{prefix}{record.text}{postfix}".strip() or record.text

    def _record_index(self, record) -> str:
        if not record:
            return ""
        return str(record.index + 1)

    def _truncate(self, text: str, limit: int = 80) -> str:
        if not text:
            return ""
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.config(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    LexDiffGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
