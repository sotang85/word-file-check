#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"

python "${ROOT_DIR}/generate_samples.py" --force >/dev/null

for case_dir in "${ROOT_DIR}"/test*; do
  [ -d "${case_dir}" ] || continue
  input_dir="${case_dir}/input"
  output_dir="${case_dir}/output"
  mkdir -p "${output_dir}"
  src_doc="${input_dir}/A.docx"
  tgt_doc="${input_dir}/B.docx"
  out_doc="${output_dir}/diff.docx"
  out_csv="${output_dir}/diff.csv"
  echo "Running $(basename "${case_dir}")"
  python "${PROJECT_DIR}/lexdiff.py" "${src_doc}" "${tgt_doc}" --out "${out_doc}" --csv "${out_csv}" --ignore punct,space --threshold 0.80
  echo "  -> DOCX: ${out_doc}"
  echo "  -> CSV : ${out_csv}"
  echo
done
