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

## 제한 사항

- 한국어/영어 문장 구분에 최적화되어 있으며 일본어는 베타 수준입니다.
- 로컬에서만 실행되며 임시 파일을 생성하지 않습니다.
- 100페이지 이하 문서를 기준으로 약 30초 내 처리를 목표로 합니다.
