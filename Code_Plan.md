# TwinMarket KR PoC — 코드 수정 상세 계획

---

> **[AI 에이전트 인수인계 지시사항]**
>
> 이 파일은 **작업 진행 로그 겸 계획서**다. Usage 한도(약 5시간)로 세션이 중단될 수 있으므로,
> **각 Stage 작업 완료 후 반드시 이 파일의 해당 Stage 섹션을 업데이트**해야 한다.
>
> ### 새 세션 시작 시 해야 할 일
> 1. 이 파일 전체를 읽고 **"완료 여부"** 컬럼을 확인한다
> 2. 가장 마지막으로 완료된 Stage의 **"완료 노트"** 섹션을 읽어 컨텍스트를 복원한다
> 3. 다음 미완료 Stage부터 이어서 진행한다
>
> ### 각 Stage 완료 후 업데이트 규칙
> 해당 Stage의 섹션 끝에 아래 형식으로 **완료 노트**를 추가한다:
>
> ```
> #### ✅ 완료 노트 (YYYY-MM-DD)
> - **수행한 것**: 실제로 어떤 파일을 어떻게 수정/생성했는지
> - **핵심 판단**: 계획과 달라진 점이 있다면 왜 그렇게 결정했는지
> - **발견한 문제**: 예상과 다른 코드 구조, 에러, 주의사항
> - **다음 Stage 준비**: 다음 작업자가 바로 시작하려면 알아야 할 것
> ```
>
> Stage를 진행하기 전에 이 지시사항을 다시 읽고, 완료 후 반드시 업데이트할 것.

---

> 기준 브랜치: `aicp_twinmarket/` 원본  
> 작성일: 2026-05-13

---

## Stage 0. 준비 작업 (코드 수정 없음)

### 0-1. 작업 디렉토리 구조 확인

```
aicp_twinmarket/
├── data/
│   ├── sys_100.db            ← 원본 보존 (복사본으로 작업)
│   ├── sorted_impact_news.pkl
│   └── [신규]
│       ├── sys_100_kr.db     ← Block 1 결과물
│       ├── stock_data_kr.csv ← Block 2 결과물
│       ├── trading_days_kr.csv
│       └── samsung_news.pkl
├── util/belief/
│   ├── belief_100.csv        ← 원본 보존
│   └── [신규] belief_100_kr.csv ← Block 3 결과물
└── script/
    └── [신규] kr/
        ├── prepare_kr_data.py
        ├── build_kr_news.py
        ├── init_kr_profiles.py
        └── init_kr_beliefs.py
```

### 0-2. 원본 DB 백업

```bash
cp data/sys_100.db data/sys_100_original_backup.db
```

---

## Stage 1. 데이터 준비 스크립트 작성

### Stage 1-1. 삼성전자 주가 데이터 (script/kr/prepare_kr_data.py)

**목적**: KRX 삼성전자 OHLCV + 기술지표 → `data/stock_data_kr.csv`

**필요 라이브러리**: `FinanceDataReader`, `pykrx`, `pandas`, `numpy`

**출력 컬럼** (StockData 테이블과 동일):

```python
columns = [
    "stock_id",       # "005930" 고정
    "date",           # YYYY-MM-DD
    "close_price",    # 종가
    "pre_close",      # 전일 종가
    "change",         # 등락액
    "pct_chg",        # 등락률(%)
    "pe_ttm",         # PER (pykrx 또는 별도 소스)
    "pb",             # PBR
    "ps_ttm",         # PSR (없으면 0)
    "dv_ttm",         # 배당수익률 (없으면 0)
    "vol",            # 거래량
    "vol_5",          # 5일 평균 거래량
    "vol_10",
    "vol_30",
    "ma_hfq_5",       # 5일 이동평균
    "ma_hfq_10",
    "ma_hfq_30",
    "elg_amount_net", # 기관+외국인 순매수 (pykrx investor 데이터)
]
```

**처리 로직**:
1. `fdr.DataReader("005930", start, end)` 또는 `pykrx.stock.get_market_ohlcv_by_date()`
2. MA 계산: `rolling(5/10/30).mean()`
3. 거래량 MA: 동일 rolling
4. elg_amount_net: `pykrx.stock.get_market_trading_value_by_date()` 기관+외국인 합산
5. pe_ttm, pb: `pykrx.stock.get_market_fundamental_by_date()`
6. CSV 저장: `data/stock_data_kr.csv`

**기간**: 시뮬레이션 시작 최소 30 거래일 전부터 (MA30 계산 위해)

---

### Stage 1-2. 한국 거래 캘린더 (script/kr/prepare_kr_data.py 내 포함)

**출력**: `data/trading_days_kr.csv`

**컬럼**: `cal_date`, `is_open`, `pretrade_date`

**방법**:
```python
from pykrx import stock
# stock.get_market_ohlcv_by_date()로 실거래일만 추출
# 또는 holidays 패키지 + 주말 제외
```

---

### Stage 1-3. 초기 DB 생성 (script/kr/init_kr_profiles.py)

**목적**: `sys_100.db` 복사 후 한국화 → `data/sys_100_kr.db`

**처리 순서**:

```python
# Step A: DB 복사
shutil.copy("data/sys_100.db", "data/sys_100_kr.db")

# Step B: TradingDetails 전체 삭제
conn.execute("DELETE FROM TradingDetails")

# Step C: Profiles 갱신 (최신 created_at 행만 대상)
# 각 유저의 2023-06-14 행을 기준으로:

for user in all_users:
    # ini_cash 변환
    if original_ini_cash <= 10_000_000:  # 1000만 위안 이하
        new_ini_cash = random.randint(100_000_000, 300_000_000)  # 1억~3억원
    else:  # 1억 위안
        new_ini_cash = random.randint(500_000_000, 1_000_000_000)  # 5억~10억원

    # 포지션 완전 초기화
    # UPDATE Profiles SET
    #   ini_cash           = new_ini_cash,
    #   current_cash       = new_ini_cash,
    #   total_value        = new_ini_cash,
    #   total_return       = 0,
    #   return_rate        = 0.0,
    #   cur_positions      = '{}',
    #   initial_positions  = '{"005930": 0}',
    #   stock_returns      = '{}',
    #   yest_returns       = '{}',
    #   fol_ind            = '["전기전자", "반도체"]'
    # WHERE user_id = ? AND created_at = '2023-06-14 00:00:00'

# Step D: StockData 초기화 (한국 종목 코드로 초기 행 삽입)
# 005930 기준 시작일 이전 30일치 데이터를 stock_data_kr.csv에서 읽어서 INSERT
```

---

### Stage 1-4. Belief 재생성 (script/kr/init_kr_beliefs.py)

**목적**: `util/init_belief.py`의 프롬프트를 한국 시장 버전으로 변경 → `util/belief/belief_100_kr.csv`

**수정할 핵심 프롬프트** (`init_belief.py:get_init_prompt()` 참조):

```python
# 기존
SYSTEM_PROMPT = "你是一位专注于中国A股市场的投资者..."

# 변경
SYSTEM_PROMPT = """당신은 한국 KOSPI 시장에서 삼성전자(005930) 주식에 투자하는 투자자입니다.
삼성전자는 메모리 반도체(DRAM/NAND), 스마트폰, 디스플레이 사업을 영위하는
KOSPI 시가총액 1위 기업입니다..."""
```

**belief 생성 내용 유지**:
- 시장 트렌드, 시장 밸류에이션, 경제 상황, 시장 심리, 자기 평가 5개 항목
- attitude 비율: 낙관 40% / 중립 10% / 비관 50% **그대로 유지**
- LLM 호출 로직 (retry 3회, fallback) 동일

---

### Stage 1-5. 뉴스 데이터 수집 (script/kr/build_kr_news.py)

**목적**: 삼성전자 한국어 뉴스 스크래핑 → `data/samsung_news.pkl`

**출력 포맷** (기존 pkl과 동일):
```python
# DataFrame
# cal_date (str): "YYYY-MM-DD"
# news (list[str]): 해당 날짜 뉴스 텍스트 배열
```

**수집 방법**: NAVER Finance 뉴스 스크래핑 (005930 종목 뉴스)

**임베딩 인덱스**: `data/InformationDB_samsung/` 디렉토리에 FAISS 인덱스 생성
- 모델: `paraphrase-multilingual-MiniLM-L12-v2` (한국어 지원 확인됨)
- InformationDB.build_database() 활용

---

## Stage 2. 엔진 수정

### Stage 2-1. trader/utility.py

**수정 대상**: `_STOCK_PROFILE_DICT_RAW` (line ~147)

```python
# 기존: 10개 중국 인덱스 딕셔너리 삭제
# 변경:
_STOCK_PROFILE_DICT_RAW = {
    "005930": (
        "삼성전자(KRX:005930)는 대한민국 대표 전기전자·반도체 기업이다. "
        "KOSPI 시가총액 1위 종목으로, 메모리 반도체(DRAM/NAND), "
        "스마트폰(갤럭시), 디스플레이 사업을 영위한다."
    )
}
```

**추가 확인**: `init_system()` 함수 내 종목 코드 하드코딩 여부 검토 후 교체

---

### Stage 2-2. trader/matching_engine.py

**수정 1: 가격 제한** (line ~320-321)

```python
# 기존
upper_limit = last_price * 1.1
lower_limit = last_price * 0.9

# 변경
upper_limit = last_price * 1.3  # ±30% (KRX)
lower_limit = last_price * 0.7
```

**수정 2: 주석/설명** (line ~34, ~267) — 언급된 ±10% 텍스트 전체 교체

**수정 3: 거래 단위는 matching_engine에서는 별도 처리 없음** (이미 trading_agent에서 처리됨)

---

### Stage 2-3. trader/trading_agent.py

**수정 1: 거래 단위** (line ~239-253)

```python
# 기존
if quantity < 100:
    quantity = 100
else:
    quantity = (quantity // 100) * 100

# 변경 (매수/매도 모두)
quantity = max(1, int(quantity))
```

**수정 2: use_community 파라미터 추가** (`__init__` 시그니처)

```python
def __init__(self, ..., use_community: bool = True, ...):
    self.use_community = use_community
```

**수정 3: input_info() 내 커뮤니티 조건부 실행** (line ~541-548, ~915)

```python
# 포럼 읽기/반응 (line ~541)
if self.use_community and not day_1st:
    # recommend_post_graph 호출
    ...
else:
    forum_args = None

# 게시글 작성 (line ~915 _intention_agent)
if self.use_community:
    # _intention_agent 호출
    ...
else:
    post_response_args = None
```

**수정 4: stocks_to_deal 고정** (stock_selection 단계)

```python
# 기존: LLM에게 종목 선택 요청
# 변경: 단일 종목이므로 고정
stocks_to_deal = list(user_profile["cur_positions"].keys()) or ["005930"]
# → get_stock_selection_prompt 호출 제거 (LLM 불필요)
```

---

### Stage 2-4. trader/prompts.py

**수정 1: 강제 거래 조항 제거** (line ~696)

```python
# 삭제: "你必须选择至少一个指数进行buy或者sell类型的交易，否则会受到惩罚"
# 변경: hold도 유효한 선택임을 명시
"hold도 완전히 유효한 결정입니다. 현재 시장 상황과 포트폴리오에 따라
 buy / hold / sell 중 가장 적합한 결정을 자유롭게 내리세요."
```

**수정 2: 강제 선택 조항 제거** (line ~468)

```python
# 삭제: "至少选择一个指数进行交易"
# → get_stock_selection_prompt 자체가 제거되므로 불필요
```

**수정 3: 종목 단위 한국어화**

- `format_date()`: 한국어 요일 포맷 이미 지원됨 (weekday_map 존재) → 유지
- `get_system_prompt_new()`: "中国A股市场投资者" → "한국 KOSPI 삼성전자 투자자"
- `get_decision_prompt()`: "元" → "원", "指数" → "삼성전자"

---

### Stage 2-5. util/UserDB.py — build_graph_new() 재설계

**함수 위치**: line ~563-738

**기존 알고리즘**: TradingDetails.industry 필드 기반 weighted Jaccard  
**신규 알고리즘**: 보유 비율 유사도 + Belief 텍스트 유사도

```python
def build_graph_new_single_stock(
    db_path: str,
    forum_db_path: str,
    current_date: str,
    similarity_threshold: float = 0.2,
    save_name: str = "user_graph",
    save: bool = True,
) -> nx.Graph:
    """
    단일종목 환경을 위한 소셜 그래프 구축
    연결 강도 = 보유비율 유사도(0.5) + Belief 코사인 유사도(0.5)
    """
    # Step 1: 각 유저의 최신 포지션 비율 로드
    #   cur_positions["005930"]["ratio"] (없으면 0)

    # Step 2: 각 유저의 최신 belief 로드 (forum_db posts 테이블)
    #   가장 최근 belief 텍스트 → 임베딩 벡터화

    # Step 3: 페어별 유사도 계산
    #   position_sim = 1 - |ratio_i - ratio_j| / 100
    #   belief_sim = cosine_similarity(vec_i, vec_j)
    #   total_sim = 0.5 * position_sim + 0.5 * belief_sim

    # Step 4: threshold 이상인 페어에 엣지 추가
    #   (초기: TradingDetails 없으면 belief_sim만 사용)

    # Step 5: 고립 노드 처리 (기존 로직 재사용)
```

**중요**: 초기 시뮬레이션 시 TradingDetails가 비어있으므로 belief 유사도만으로 초기 그래프 생성.

---

### Stage 2-6. simulation.py

**수정 1: use_community 파라미터 추가**

```python
def init_simulation(
    ...,
    use_community: bool = True,        # 신규
    stock_code: str = "005930",        # 신규
    stock_data_path: str = "data/stock_data_kr.csv",  # 변경
    trading_days_path: str = "data/trading_days_kr.csv",  # 변경
    news_path: str = "data/samsung_news.pkl",  # 변경
    ...
):
```

**수정 2: process_user_input() 호출에 use_community 전달**

```python
executor.submit(
    process_user_input,
    ...,
    use_community,  # 추가
)
```

**수정 3: 커뮤니티 OFF 시 스킵 블록**

```python
# forum_args 처리 블록
if use_community and not day_1st:
    asyncio.run(execute_forum_actions(...))
    update_posts_score_by_date_range(...)

# post 처리 블록 (게시글 작성)
# use_community=False면 post_response_args가 None → 자동 스킵됨 (기존 체크 로직 재사용)
```

**수정 4: build_graph_new → build_graph_new_single_stock 교체**

```python
# 기존
current_user_graph = build_graph_new(
    similarity_threshold=..., time_decay_factor=..., db_path=user_db, ...
)

# 변경
current_user_graph = build_graph_new_single_stock(
    db_path=user_db,
    forum_db_path=forum_db,
    current_date=current_date.strftime("%Y-%m-%d"),
    similarity_threshold=similarity_threshold,
)
```

**수정 5: argparse에 신규 파라미터 추가**

```python
parser.add_argument("--use_community", type=lambda x: x.lower()=='true', default=True)
parser.add_argument("--stock_code", type=str, default="005930")
parser.add_argument("--stock_data_path", type=str, default="data/stock_data_kr.csv")
parser.add_argument("--trading_days_path", type=str, default="data/trading_days_kr.csv")
parser.add_argument("--news_path", type=str, default="data/samsung_news.pkl")
```

---

## Stage 3. 검증

### Stage 3-1. Smoke Test

```bash
python simulation.py \
  --start_date 2024-06-03 --end_date 2024-06-04 \
  --stock_code 005930 \
  --use_community False \
  --node 10 \
  --user_db data/sys_100_kr.db \
  --forum_db data/forum_kr.db \
  --belief_init_path util/belief/belief_100_kr.csv \
  --stock_data_path data/stock_data_kr.csv \
  --trading_days_path data/trading_days_kr.csv \
  --news_path data/samsung_news.pkl
```

**체크포인트**:
- [ ] 에러 없이 2일 완주
- [ ] `logs/trading_records/2024-06-03.json` 생성 및 005930 포함
- [ ] `logs/daily_summary_2024-06-03.csv` 종가 갱신 확인
- [ ] DB `StockData` 테이블에 005930 행 추가 확인
- [ ] 포지션/현금 업데이트 정상 확인

### Stage 3-2. Community OFF 실험 (20일)

```bash
python simulation.py \
  --start_date 2024-07-01 --end_date 2024-07-31 \
  --use_community False \
  --node 100 \
  --user_db data/sys_100_kr.db \
  --forum_db data/forum_kr_off.db \
  --log_dir logs_kr_off
```

### Stage 3-3. Community ON 실험 (동일 20일)

```bash
python simulation.py \
  --start_date 2024-07-01 --end_date 2024-07-31 \
  --use_community True \
  --node 100 \
  --user_db data/sys_100_kr.db \
  --forum_db data/forum_kr_on.db \
  --log_dir logs_kr_on
```

---

## 수정 파일 요약

| Stage | 파일 | 수정 유형 | 핵심 변경 |
|-------|------|---------|---------|
| 1-1 | `script/kr/prepare_kr_data.py` | 신규 | 삼성전자 데이터 수집 |
| 1-3 | `script/kr/init_kr_profiles.py` | 신규 | DB 초기화 + ini_cash 변환 |
| 1-4 | `script/kr/init_kr_beliefs.py` | 신규 | 한국 시장 belief 생성 |
| 1-5 | `script/kr/build_kr_news.py` | 신규 | 뉴스 스크래핑 + FAISS |
| 2-1 | `trader/utility.py` | 기존 수정 | STOCK_PROFILE_DICT 교체 |
| 2-2 | `trader/matching_engine.py` | 기존 수정 | ±10% → ±30% |
| 2-3 | `trader/trading_agent.py` | 기존 수정 | 단위 변경, community 토글 |
| 2-4 | `trader/prompts.py` | 기존 수정 | 강제 거래 제거, 한국어화 |
| 2-5 | `util/UserDB.py` | 기존 수정 | 그래프 알고리즘 교체 |
| 2-6 | `simulation.py` | 기존 수정 | use_community, 경로 파라미터 |

---

*작성: 2026-05-13 | 실행 순서: Stage 1 → Stage 2 → Stage 3*
