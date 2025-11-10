"""lexdiff 올인원 실행기.

이 스크립트는 가상환경 생성, 의존성 설치, 실행 모드 선택을 한 번에 처리해
GUI/웹/CLI 인터페이스를 쉽게 실행할 수 있도록 돕습니다.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict

ROOT_DIR = Path(__file__).resolve().parent
VENV_DIR = ROOT_DIR / ".venv"


class LauncherError(RuntimeError):
    """사용자에게 안내할 수 있는 런처 오류."""


def _is_windows() -> bool:
    return os.name == "nt"


def _venv_python(venv_dir: Path) -> Path:
    if _is_windows():
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _in_target_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except FileNotFoundError:
        return False


def _run_command(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd or ROOT_DIR, check=check)


def _create_venv() -> None:
    print("가상환경이 없어 새로 생성합니다 (.venv).")
    _run_command([sys.executable, "-m", "venv", str(VENV_DIR)])


def _dependencies_installed(python_bin: Path) -> bool:
    check_code = (
        "import importlib.util, sys;\n"
        "modules = ['docx', 'flask'];\n"
        "missing = [m for m in modules if importlib.util.find_spec(m) is None];\n"
        "sys.exit(0 if not missing else 1)"
    )
    result = subprocess.run([str(python_bin), "-c", check_code], cwd=ROOT_DIR)
    return result.returncode == 0


def _install_requirements(python_bin: Path) -> None:
    print("필수 패키지를 설치합니다 (requirements.txt).")
    _run_command([str(python_bin), "-m", "pip", "install", "-r", str(ROOT_DIR / "requirements.txt")])


def _ensure_environment() -> Path:
    if _in_target_venv():
        python_bin = Path(sys.executable)
    else:
        python_bin = _venv_python(VENV_DIR)
        if not python_bin.exists():
            _create_venv()
        python_bin = _venv_python(VENV_DIR)

    if not _dependencies_installed(python_bin):
        _install_requirements(python_bin)
        if not _dependencies_installed(python_bin):
            raise LauncherError("의존성 설치에 실패했습니다. 인터넷 연결과 권한을 확인하세요.")

    return python_bin


def _run_gui(python_bin: Path) -> None:
    print("Tkinter GUI를 실행합니다. 창을 닫으면 런처로 돌아옵니다.")
    _run_command([str(python_bin), "lexdiff_gui.py"], check=False)


def _run_web(python_bin: Path) -> None:
    print("웹 인터페이스를 실행합니다. 브라우저에서 http://127.0.0.1:5000 으로 접속하세요.")
    print("종료하려면 Ctrl+C 를 누르세요.")
    _run_command([str(python_bin), "lexdiff_web.py"], check=False)


def _run_cli(python_bin: Path) -> None:
    print("CLI 실행을 위한 정보를 입력하세요. 빈 값은 취소로 처리됩니다.")
    src = input("원본 DOCX 경로: ").strip()
    if not src:
        print("취소했습니다.")
        return
    tgt = input("수정 DOCX 경로: ").strip()
    if not tgt:
        print("취소했습니다.")
        return
    out_doc = input("하이라이트 DOCX 출력 (기본=out.docx): ").strip() or "out.docx"
    out_csv = input("CSV 출력 (기본=diff.csv): ").strip() or "diff.csv"
    extra = input("추가 옵션 (예: --ignore punct,space --threshold 0.85): ").strip()
    cmd = [str(python_bin), "lexdiff.py", src, tgt, "--out", out_doc, "--csv", out_csv]
    if extra:
        cmd.extend(shlex.split(extra, posix=not _is_windows()))
    print("\n명령 실행 중...\n")
    _run_command(cmd, check=False)


def _run_samples(python_bin: Path) -> None:
    print("샘플 문서를 생성하고 비교합니다.")
    _run_command([str(python_bin), "samples/generate_samples.py", "--force"])
    samples_dir = ROOT_DIR / "samples"
    for case in sorted(samples_dir.glob("test*")):
        if not case.is_dir():
            continue
        input_dir = case / "input"
        output_dir = case / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        src = input_dir / "A.docx"
        tgt = input_dir / "B.docx"
        out_doc = output_dir / "diff.docx"
        out_csv = output_dir / "diff.csv"
        print(f"- {case.name} 비교 중")
        cmd = [
            str(python_bin),
            "lexdiff.py",
            str(src),
            str(tgt),
            "--out",
            str(out_doc),
            "--csv",
            str(out_csv),
            "--ignore",
            "punct,space",
            "--threshold",
            "0.80",
        ]
        _run_command(cmd)
        print(f"  DOCX: {out_doc}")
        print(f"  CSV : {out_csv}\n")
    print("샘플 실행이 완료되었습니다.")


def _prompt_action() -> str:
    print(
        """
==============================
lexdiff 런처
==============================
1) Tkinter GUI 실행
2) 웹 인터페이스 실행
3) CLI 실행
4) 샘플 비교 실행
q) 종료
""".strip()
    )
    return input("메뉴 번호를 선택하세요 (기본=1): ").strip().lower() or "1"


def _pause_if_needed() -> None:
    try:
        if sys.stdin.isatty():
            return
    except Exception:
        pass
    try:
        input("\n계속하려면 Enter 키를 누르세요...")
    except EOFError:
        pass


def main() -> int:
    try:
        python_bin = _ensure_environment()
    except LauncherError as err:
        print(f"오류: {err}")
        _pause_if_needed()
        return 1
    except subprocess.CalledProcessError as err:
        print("명령 실행 중 오류가 발생했습니다.")
        print(f"  명령: {' '.join(err.cmd)}")
        print(f"  코드 : {err.returncode}")
        _pause_if_needed()
        return err.returncode or 1

    actions: Dict[str, Callable[[Path], None]] = {
        "1": _run_gui,
        "2": _run_web,
        "3": _run_cli,
        "4": _run_samples,
    }

    try:
        while True:
            choice = _prompt_action()
            if choice in {"q", "quit", "exit"}:
                print("런처를 종료합니다.")
                break
            action = actions.get(choice)
            if not action:
                print("지원하지 않는 선택입니다. 다시 입력하세요.\n")
                continue
            action(python_bin)
    except KeyboardInterrupt:
        print("\n사용자 요청으로 종료합니다.")
    finally:
        _pause_if_needed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
