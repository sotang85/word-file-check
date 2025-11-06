#!/usr/bin/env python3
"""Flask 웹 애플리케이션 – 새 엔진과 UI에 맞게 재작성."""
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

from lexdiff import DependencyError, DiffRow, run_diff

app = Flask(__name__, template_folder="webapp/templates", static_folder="webapp/static")
app.secret_key = os.environ.get("LEXDIFF_SECRET_KEY", "lexdiff-web-ui")

_RESULT_CACHE: Dict[str, Dict[str, object]] = {}
_CACHE_TTL = 600  # seconds


def _cleanup_cache() -> None:
    now = time.time()
    expired = [token for token, payload in _RESULT_CACHE.items() if now - payload["created"] > _CACHE_TTL]
    for token in expired:
        _RESULT_CACHE.pop(token, None)


def _present_rows(rows: Iterable[DiffRow]) -> List[dict]:
    mapping = {"add": "add", "del": "delete", "replace": "replace"}
    presented: List[dict] = []
    for row in rows:
        type_key = mapping.get(row.type, row.type)
        presented.append(
            {
                "type": type_key,
                "sim": row.sim,
                "original": row.original,
                "revised": row.revised,
                "idxA": row.idxA or "-",
                "idxB": row.idxB or "-",
            }
        )
    return presented


def _summarize(rows: Iterable[DiffRow]) -> Dict[str, int]:
    summary = {"add": 0, "delete": 0, "replace": 0}
    for row in rows:
        if row.type == "add":
            summary["add"] += 1
        elif row.type == "del":
            summary["delete"] += 1
        elif row.type == "replace":
            summary["replace"] += 1
    return summary


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

                result = run_diff(
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
        except DependencyError as exc:
            flash(str(exc))
            return render_template("index.html", form=form_values, ignore_selected=ignore_tokens)
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

        rows = _present_rows(result.rows)
        summary = _summarize(result.rows)

        return render_template(
            "index.html",
            form=form_values,
            ignore_selected=ignore_tokens,
            operations=rows,
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
        data = payload.get("docx")
        filename = payload.get("docx_name", "lexdiff_result.docx")
        mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "csv":
        data = payload.get("csv")
        filename = payload.get("csv_name", "lexdiff_diff.csv")
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


if __name__ == "__main__":  # pragma: no cover - manual execution only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
