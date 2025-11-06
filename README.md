# lexdiff

문장 단위로 두 개의 DOCX 파일을 비교하고 변경 사항을 하이라이트한 Word 문서와 CSV 리포트를 생성하는 CLI 도구입니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 사용 방법

```bash
python lexdiff.py A.docx B.docx --out out.docx --csv diff.csv --ignore punct,space --threshold 0.80
```

- `--out`: 변경 사항을 표시한 DOCX 출력 경로
- `--csv`: 변경 내역을 기록한 CSV 경로
- `--ignore`: 비교 시 무시할 요소. `punct`, `space` 조합을 콤마로 구분하여 지정
- `--threshold`: 문장 교체로 분류하기 위한 최소 유사도 (0~1)

## GUI 실행

CLI 대신 간단한 시각화 인터페이스를 사용하려면 Tkinter 기반 GUI를 실행하세요.

```bash
python lexdiff_gui.py
```

프로그램에서 원본·수정 DOCX 파일과 결과 저장 위치를 선택하고, 옵션(구두점/공백 무시, 임계값)을 조정한 뒤 **비교 실행** 버튼을 누르면 됩니다. 실행이 끝나면 하단 테이블과 텍스트 영역에서 변경 문장을 즉시 미리 확인할 수 있으며, 생성된 DOCX/CSV는 지정한 경로에 저장됩니다.

=======
## 웹 인터페이스 실행

브라우저에서 업로드와 다운로드만으로 비교 작업을 처리하고 싶다면 Flask 기반 웹 애플리케이션을 실행하세요.

```bash
python lexdiff_web.py
```

위 명령은 자동으로 `0.0.0.0:5000`에 서버를 열어 Codespaces, Docker 컨테이너 등 포트 포워딩 환경에서도 바로 접속할 수 있습니다. 만약 `flask run` 명령을 사용하고 싶다면 다음과 같이 호스트와 포트를 명시해야 동일하게 외부에서 접근할 수 있습니다.

```bash
FLASK_APP=lexdiff_web.py flask run --host 0.0.0.0 --port 5000
```

페이지가 열리면 DOCX 파일 두 개를 업로드하고 옵션(무시 규칙, 임계값, 출력 파일명)을 지정한 뒤 **비교 실행**을 클릭하면 됩니다. 결과는 페이지 내 테이블로 미리보기되고, 같은 화면에서 하이라이트 DOCX와 CSV 리포트를 즉시 내려받을 수 있습니다. 결과 파일은 메모리에만 보관되며 10분 후 자동으로 삭제됩니다.

## 출력 형식

- DOCX: 추가 문장은 밑줄, 삭제 문장은 취소선, 수정 문장은 단어 단위로 노란색 하이라이트 표시됩니다.
- CSV: `type, sim, original, revised, idxA, idxB` 열을 가지며, 숫자 변경이 있는 경우 `revised` 열에 Δ 값이 표시됩니다.

## 예시 데이터

`samples/` 폴더에 3개의 샘플 케이스가 포함되어 있습니다. 저장소에는 이 케이스를 생성하는 스크립트만 포함되며, 필요할 때 아래 명령으로 DOCX 입력 파일을 만들 수 있습니다.

```bash
python samples/generate_samples.py
```

모든 샘플을 한 번에 실행하려면 다음 명령을 사용하세요. 스크립트는 실행 전에 입력 DOCX를 자동으로 재생성합니다.

```bash
bash samples/run_samples.sh
```

각 샘플은 `input` 폴더에 원본/수정 문서를, `output` 폴더에 결과 DOCX 및 CSV를 생성합니다.

=======
## GitHub Codespaces에서 빠른 실행

GitHub Codespaces에서는 기본적으로 Python이 준비되어 있으므로 아래 단계만 수행하면 됩니다.

1. **터미널 열기**: Codespaces 창에서 `Terminal → New Terminal`을 선택합니다.
2. **가상환경 생성 및 활성화** (선택 사항이지만 권장):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **필수 패키지 설치**:

   ```bash
   pip install -r requirements.txt
   ```

4. **GUI 실행** (시각화 환경이 필요한 경우 VS Code의 `Open in Desktop` 또는 포트 포워딩된 브라우저를 사용하세요):

   ```bash
   python lexdiff_gui.py
   ```

   웹 브라우저에서 직접 비교하려면 포트 포워딩 후 아래 명령으로 Flask 앱을 실행하세요.

   ```bash
   python lexdiff_web.py  # 0.0.0.0:5000에 바로 개방
   ```

   Codespaces의 내장 `flask run` 명령을 쓰는 경우에는 반드시 `--host 0.0.0.0 --port 5000` 옵션을 지정해야 외부 접속이 가능합니다.

5. **CLI 실행 예시**:

   ```bash
   python lexdiff.py A.docx B.docx --out out.docx --csv diff.csv --ignore punct,space --threshold 0.80
   ```

6. **샘플 테스트** (샘플 입력/출력을 자동 생성):

   ```bash
   bash samples/run_samples.sh
   ```

필요에 따라 `pip install --upgrade pip`으로 패키지 관리자를 최신 상태로 맞춘 뒤 위 명령을 실행해도 됩니다.

## PR 생성 관련 안내

이 프로젝트는 Codex 환경에서 작업한 뒤 `make_pr` 도구로 PR을 올리도록 구성되어 있습니다. 이미 외부에서 동일 브랜치에 연결된 PR이 존재할
경우 Codex 측에서 "Codex에서는 현재 외부에서 업데이트된 PR 업데이트를 지원하지 않습니다. 새로운 PR을 생성해 주세요."라는 메시지가 나타날
수 있습니다. 이는 기존 PR을 갱신할 수 없음을 의미하므로, 변경 사항을 커밋한 뒤 `make_pr` 호출 시 **새로운 제목과 설명으로 PR을 다시 생성**하면
정상적으로 제출할 수 있습니다.

## 제한 사항

- 한국어/영어 문장 구분에 최적화되어 있으며 일본어는 베타 수준입니다.
- 로컬에서만 실행되며 임시 파일을 생성하지 않습니다.
- 100페이지 이하 문서를 기준으로 약 30초 내 처리를 목표로 합니다.
