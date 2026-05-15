# Stage 1 Pipeline Execution Report

작성일: 2026-05-14
작업 디렉터리: `/Users/leeyujeong/Desktop/TwinMarket`
브랜치: `codex/implement-stage-1-1-to-stage-1-5`

## 1. 실행 요약

- 최종 상태: 성공
- Stage 1-1/1-2: `data/stock_data_kr.csv`, `data/trading_days_kr.csv` 생성 성공
- Stage 1-3: `data/sys_100_kr.db` 생성 및 `TradingDetails` 초기화 성공
- Stage 1-4: `util/belief/belief_100_kr.csv` 생성 성공
- Stage 1-5: `data/samsung_news.pkl`, `data/InformationDB_samsung/` 생성 성공
- 자동 수정: `script/kr/build_kr_news.py`에 pandas StringDtype pickle 호환 fallback 로더 추가
- GitHub push: 수행하지 않음

## 2. 실제 실행한 명령어

```bash
pwd
git status --short --branch
rg --files
find . -maxdepth 3 -type f \( -name 'requirements*.txt' -o -name 'pyproject.toml' -o -name 'setup.py' -o -name 'setup.cfg' -o -name 'Pipfile' -o -name 'poetry.lock' -o -name 'environment.yml' \)
sed -n '1,220p' requirements.txt
sed -n '1,260p' README.md
sed -n '1,220p' script/run.sh
rg -n "Stage 1|stage 1|stage1|Stage1|pipeline|prepare_kr|init_kr|build_kr|run.sh|simulation" .
sed -n '203,430p' Code_Plan.md
sed -n '1,260p' script/kr/prepare_kr_data.py
sed -n '1,260p' script/kr/init_kr_profiles.py
sed -n '1,260p' script/kr/init_kr_beliefs.py
sed -n '1,320p' script/kr/build_kr_news.py
python3 --version
rg -n "^(import|from) " --glob '*.py'
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
/opt/homebrew/bin/python3.10 -m venv --clear .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt finance-datareader pykrx sentence-transformers reportlab markdown
.venv/bin/python -c "import sys, pandas, numpy, faiss, FinanceDataReader, pykrx, sentence_transformers, reportlab; print(sys.version); print('imports ok')"
mkdir -p .mplconfig
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/prepare_kr_data.py --start 2025-12-01 --end 2026-03-31
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/init_kr_profiles.py
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/init_kr_beliefs.py
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/build_kr_news.py
.venv/bin/python -m pip install pandas==2.2.3
MPLCONFIGDIR=.mplconfig HF_HOME=.hf_cache .venv/bin/python script/kr/build_kr_news.py
git status --short
find data util/belief -maxdepth 2 \( -name 'stock_data_kr.csv' -o -name 'trading_days_kr.csv' -o -name 'sys_100_kr.db' -o -name 'belief_100_kr.csv' -o -name 'samsung_news.pkl' -o -name 'faiss_index.pkl' -o -name 'metadata.pkl' \) -print -exec ls -lh {} \;
MPLCONFIGDIR=.mplconfig HF_HOME=.hf_cache .venv/bin/python - <<'PY'
# 산출물 검증 스크립트 실행
PY
.venv/bin/python -m pip freeze
```

네트워크가 필요한 아래 명령은 sandbox 실패 후 승인된 네트워크 권한으로 재실행했다.

```bash
.venv/bin/python -m pip install --upgrade pip setuptools wheel
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/prepare_kr_data.py --start 2025-12-01 --end 2026-03-31
MPLCONFIGDIR=.mplconfig HF_HOME=.hf_cache .venv/bin/python script/kr/build_kr_news.py
```

## 3. 의존성 분석 및 설치

발견된 의존성 정의 파일:

- `requirements.txt`
- `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`, `poetry.lock`, `environment.yml`: 없음

`requirements.txt` 패키지:

- `aiofiles`, `aiosqlite`, `matplotlib`, `networkx`, `numpy`, `openai>=1.0.0`, `pandas`, `pyyaml`, `requests`, `tenacity`, `tqdm`, `faiss-cpu`

import 및 Stage 1 스크립트에서 추가 탐지해 설치한 패키지:

- `finance-datareader` (`import FinanceDataReader`)
- `pykrx`
- `sentence-transformers`
- `reportlab`
- `markdown`

중요 조정:

- 시스템 기본 `python3`는 3.14.3이었으나, 일부 과학/ML 패키지 호환성을 고려해 `.venv`를 `/opt/homebrew/bin/python3.10` 기반으로 재생성했다.
- `FinanceDataReader`는 PyPI 패키지명이 아니어서 설치 실패했고, 실제 패키지명인 `finance-datareader`로 설치했다.
- pandas는 원본 뉴스 pkl 호환성 확인 과정에서 `2.2.3`으로 조정했다.

## 4. 실행 결과

### Stage 1-1 / 1-2: KR 주가 데이터 및 거래일 캘린더

명령:

```bash
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/prepare_kr_data.py --start 2025-12-01 --end 2026-03-31
```

최종 결과: 성공

출력:

```text
saved data/stock_data_kr.csv rows=80
saved data/trading_days_kr.csv rows=80
```

검증:

- `stock_rows`: 80
- `stock_date_min_max`: 2025-12-01 ~ 2026-03-31
- `trading_days_rows`: 80
- `trading_days_min_max`: 2025-12-01 ~ 2026-03-31
- 컬럼: `stock_id`, `date`, `close_price`, `pre_close`, `change`, `pct_chg`, `pe_ttm`, `pb`, `ps_ttm`, `dv_ttm`, `vol`, `vol_5`, `vol_10`, `vol_30`, `ma_hfq_5`, `ma_hfq_10`, `ma_hfq_30`, `elg_amount_net`

주의:

- `pykrx` import 시 `KRX_ID`/`KRX_PW` 환경 변수 미설정 메시지가 출력됐다.
- fundamental 및 투자자 순매수 보조 API는 JSON 파싱 오류가 발생했고, 스크립트의 기존 fallback에 따라 `pe_ttm`, `pb`, `dv_ttm`, `elg_amount_net` 결측값은 0으로 채워졌다.

### Stage 1-3: 초기 KR DB 생성

명령:

```bash
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/init_kr_profiles.py
```

결과: 성공

출력:

```text
initialized KR db: data/sys_100_kr.db
```

검증:

- `data/sys_100_kr.db` 생성
- `Profiles` distinct user 수: 1000
- `TradingDetails` row 수: 0

### Stage 1-4: 초기 belief 재생성

명령:

```bash
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/init_kr_beliefs.py
```

결과: 성공

출력:

```text
saved util/belief/belief_100_kr.csv rows=100
```

### Stage 1-5: 삼성 뉴스 정규화 및 InformationDB 생성

명령:

```bash
MPLCONFIGDIR=.mplconfig HF_HOME=.hf_cache .venv/bin/python script/kr/build_kr_news.py
```

최종 결과: 성공

출력:

```text
saved news rows=80 -> data/samsung_news.pkl
saved information db -> data/InformationDB_samsung
```

검증:

- `news_rows`: 80
- 뉴스가 존재하는 날짜 수: 38
- `metadata_count`: 217
- FAISS index vectors: 217
- FAISS dimension: 384

## 5. 생성된 파일 목록

주요 산출물:

```text
data/stock_data_kr.csv                         13K
data/trading_days_kr.csv                       1.9K
data/sys_100_kr.db                             8.6M
util/belief/belief_100_kr.csv                  18K
data/samsung_news.pkl                          100K
data/InformationDB_samsung/faiss_index.pkl     326K
data/InformationDB_samsung/metadata.pkl        104K
stage1_execution_report.md
stage1_execution_report.pdf
```

실행 보조 산출물:

```text
.venv/
.mplconfig/
.hf_cache/
```

수정된 코드:

```text
script/kr/build_kr_news.py
```

수정 내용:

- pandas StringDtype pickle 호환성 오류 발생 시 원본 pkl을 덮어쓰지 않고 pickle opcode에서 `cal_date`와 `news`를 복구하는 fallback 로더 추가

## 6. Traceback 및 오류 요약

### pip 네트워크 실패

초기 pip install은 sandbox 네트워크 제한으로 실패했다.

```text
socket.gaierror: [Errno 8] nodename nor servname provided, or not known
ERROR: Could not find a version that satisfies the requirement setuptools
```

조치:

- 승인된 네트워크 권한으로 pip 설치 재실행

### 잘못된 PyPI 패키지명

명령:

```bash
.venv/bin/python -m pip install -r requirements.txt FinanceDataReader pykrx sentence-transformers reportlab markdown
```

오류:

```text
ERROR: Could not find a version that satisfies the requirement FinanceDataReader
```

조치:

- `FinanceDataReader` 대신 `finance-datareader` 설치

### 주가 수집 네트워크 실패

초기 `prepare_kr_data.py` 실행은 sandbox DNS 제한으로 실패했다.

핵심 traceback:

```text
requests.exceptions.ConnectionError:
HTTPSConnectionPool(host='fchart.stock.naver.com', port=443): Max retries exceeded
Caused by NameResolutionError: Failed to resolve 'fchart.stock.naver.com'
```

조치:

- 승인된 네트워크 권한으로 재실행하여 성공

### 주가 보조 데이터 API 파싱 오류

성공한 실행 중 보조 API에서 아래 메시지가 출력됐다.

```text
Error occurred in get_market_fundamental_by_date: Expecting value: line 1 column 1 (char 0)
Error occurred in get_market_trading_value_and_volume_on_ticker_by_date: Expecting value: line 1 column 1 (char 0)
```

조치:

- 기존 스크립트 fallback에 따라 결측값을 0으로 채움
- OHLCV 및 거래일 산출물 생성은 성공

### 뉴스 pkl pandas 호환성 오류

명령:

```bash
MPLCONFIGDIR=.mplconfig .venv/bin/python script/kr/build_kr_news.py
```

핵심 traceback:

```text
NotImplementedError: (<StringDtype(storage='python', na_value=nan)>, array([...], dtype=object))
```

pandas 2.2.3 확인 시:

```text
TypeError: StringDtype.__init__() takes from 1 to 2 positional arguments but 3 were given
```

조치:

- `script/kr/build_kr_news.py`에 `_read_news_pickle()` fallback 추가
- 원본 `data/samsung_mk_news_20260201_20260331.pkl`은 수정하지 않음

### Hugging Face 모델 다운로드 네트워크 실패

초기 `build_kr_news.py` 실행은 sandbox DNS 제한으로 실패했다.

핵심 traceback:

```text
'[Errno 8] nodename nor servname provided, or not known' thrown while requesting HEAD https://huggingface.co/...
RuntimeError: Cannot send a request, as the client has been closed.
```

조치:

- 승인된 네트워크 권한으로 재실행
- `HF_HOME=.hf_cache`를 지정해 모델 캐시를 워크스페이스 내부에 저장

### Matplotlib 캐시 경로 권한 경고

초기 import 검증 중:

```text
mkdir -p failed for path /Users/leeyujeong/.matplotlib: [Errno 1] Operation not permitted
```

조치:

- 이후 실행에서 `MPLCONFIGDIR=.mplconfig` 사용

## 7. 실행 환경 정보

```text
OS/platform: macOS-15.2-arm64-arm-64bit
Timezone: Asia/Seoul
Python: 3.10.20
Virtualenv: /Users/leeyujeong/Desktop/TwinMarket/.venv
pandas: 2.2.3
numpy: 2.2.6
faiss-cpu: 1.13.2
sentence-transformers: 5.5.0
torch: 2.12.0
reportlab: 4.5.1
```

## 8. 추천되는 다음 작업

1. `requirements.txt`에 Stage 1에서 실제 필요한 `finance-datareader`, `pykrx`, `sentence-transformers`를 추가한다.
2. Python 버전을 `3.10` 또는 프로젝트 검증 버전으로 문서화한다.
3. `prepare_kr_data.py`에서 fundamental/투자자 순매수 API 실패 시 경고와 fallback 사용 여부를 명시적으로 로그에 남긴다.
4. `data/samsung_mk_news_20260201_20260331.pkl` 생성 환경의 pandas 버전을 기록하거나, 장기적으로는 pickle 대신 CSV/Parquet/JSONL 같은 호환성이 더 좋은 포맷을 사용한다.
5. Stage 2 시뮬레이션 전에 `config/api.yaml`, `config/embedding.yaml`을 실제 키/모델 설정으로 준비한다.
6. `.venv/`, `.hf_cache/`, `.mplconfig/`는 보조 실행 산출물이므로 Git 추적 대상에서 제외하는 것이 좋다.
