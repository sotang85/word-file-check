#!/usr/bin/env python3
"""Flask web application for running lexdiff through a browser."""
from __future__ import annotations

import io
import os
import tempfile
import time
import uuid
from typing import Dict, Iterable, List

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from lexdiff import Operation, annotate_numeric_delta, run_diff


app = Flask(__name__)
app.secret_key = os.environ.get("LEXDIFF_SECRET_KEY", "lexdiff-web-ui")

_RESULT_CACHE: Dict[str, Dict[str, object]] = {}
_CACHE_TTL = 600  # seconds


def _cleanup_cache() -> None:
    now = time.time()
    expired = [token for token, payload in _RESULT_CACHE.items() if now - payload["created"] > _CACHE_TTL]
    for token in expired:
        _RESULT_CACHE.pop(token, None)


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    _cleanup_cache()

    if request.method == "POST":
        source = request.files.get("source")
        target = request.files.get("target")
        ignore_tokens = request.form.getlist("ignore")
        threshold_raw = request.form.get("threshold", "0.8")
        out_docx_name = request.form.get("docx_name", "lexdiff_result.docx") or "lexdiff_result.docx"
        out_csv_name = request.form.get("csv_name", "lexdiff_diff.csv") or "lexdiff_diff.csv"
        form_values = {
            "threshold": threshold_raw,
            "docx_name": out_docx_name,
            "csv_name": out_csv_name,
        }

        if not source or not source.filename:
            flash("원본 DOCX 파일을 선택하세요.")
            return render_template("index.html", form=form_values, ignore_selected=ignore_tokens)
        if not target or not target.filename:
            flash("수정된 DOCX 파일을 선택하세요.")
            return render_template("index.html", form=form_values, ignore_selected=ignore_tokens)

        try:
            threshold = float(threshold_raw)
        except ValueError:
            flash("임계값은 0과 1 사이의 숫자여야 합니다.")
            return render_template("index.html", form=form_values, ignore_selected=ignore_tokens)
        if not 0 <= threshold <= 1:
            flash("임계값은 0과 1 사이여야 합니다.")
            return render_template("index.html", form=form_values, ignore_selected=ignore_tokens)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = os.path.join(tmpdir, "source.docx")
                target_path = os.path.join(tmpdir, "target.docx")
                out_docx_path = os.path.join(tmpdir, "result.docx")
                out_csv_path = os.path.join(tmpdir, "result.csv")

                source.save(source_path)
                target.save(target_path)

                operations = run_diff(
                    source=source_path,
                    target=target_path,
                    out_docx=out_docx_path,
                    out_csv=out_csv_path,
                    ignore_tokens=ignore_tokens,
                    threshold=threshold,
                )

                with open(out_docx_path, "rb") as docx_file:
                    docx_bytes = docx_file.read()
                with open(out_csv_path, "rb") as csv_file:
                    csv_bytes = csv_file.read()
        except Exception as exc:  # pylint: disable=broad-except
            flash(f"비교 중 오류가 발생했습니다: {exc}")
            return render_template("index.html", form=form_values, ignore_selected=ignore_tokens)

        token = uuid.uuid4().hex
        _RESULT_CACHE[token] = {
            "created": time.time(),
            "docx": docx_bytes,
            "csv": csv_bytes,
            "docx_name": out_docx_name,
            "csv_name": out_csv_name,
        }

        display_operations = _format_operations(operations)
        summary = _summarize_operations(operations)

        return render_template(
            "index.html",
            form=form_values,
            ignore_selected=ignore_tokens,
            operations=display_operations,
            summary=summary,
            token=token,
            docx_name=out_docx_name,
            csv_name=out_csv_name,
        )

    return render_template(
        "index.html",
        form={
            "threshold": "0.8",
            "docx_name": "lexdiff_result.docx",
            "csv_name": "lexdiff_diff.csv",
        },
        ignore_selected=[],
    )


@app.route("/download/<token>/<fmt>")
def download(token: str, fmt: str) -> Response:
    _cleanup_cache()
    payload = _RESULT_CACHE.get(token)
    if not payload:
        flash("결과가 만료되었거나 찾을 수 없습니다. 다시 실행해주세요.")
        return redirect(url_for("index"))

    if fmt == "docx":
        data = payload["docx"]
        filename = payload["docx_name"]
        mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "csv":
        data = payload["csv"]
        filename = payload["csv_name"]
        mimetype = "text/csv"
    else:
        flash("지원하지 않는 형식입니다.")
        return redirect(url_for("index"))

    if not isinstance(data, (bytes, bytearray)):
        flash("결과 파일을 불러올 수 없습니다. 다시 실행해주세요.")
        return redirect(url_for("index"))

    buffer = io.BytesIO(data)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=str(filename), mimetype=mimetype)


def _format_operations(operations: Iterable[Operation]) -> List[dict]:
    formatted: List[dict] = []
    for op in operations:
        if op.get("type") == "equal":
            continue
        original = op.get("a").text if op.get("a") else ""
        revised = op.get("b").text if op.get("b") else ""
        if op.get("type") == "replace":
            revised = annotate_numeric_delta(original, revised)
        formatted.append(
            {
                "type": op.get("type"),
                "sim": f"{op.get('sim', 0.0):.2f}",
                "original": original,
                "revised": revised,
                "idxA": op.get("a").index + 1 if op.get("a") else "-",
                "idxB": op.get("b").index + 1 if op.get("b") else "-",
            }
        )
    return formatted


def _summarize_operations(operations: Iterable[Operation]) -> Dict[str, int]:
    summary = {"add": 0, "delete": 0, "replace": 0}
    for op in operations:
        op_type = op.get("type")
        if op_type in summary:
            summary[op_type] += 1
    return summary


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
