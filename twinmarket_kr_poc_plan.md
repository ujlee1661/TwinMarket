# TwinMarket → 삼성전자 단일종목 한국시장 PoC 플랜

## Context

TwinMarket은 중국 A주 시장을 기반으로 설계된 LLM 기반 주식시장 시뮬레이터다.
이 PoC의 목표는 두 가지다:

1. **데이터 호환성 검증**: 중국 기반 Persona 프로파일을 한국 시장(삼성전자 단일종목)에 적용했을 때 시장 재현력(price dynamics, volatility clustering)이 어느 정도 유지되는가?
2. **미시행동 분석 기반 구축**: TwinMarket 논문이 "커뮤니티 ON → 거시 재현력 향상"을 보였다면, 우리는 **커뮤니티 ON/OFF 시 개별 에이전트의 행동 패턴 변화**를 분석한다. (거시 → 다시 미시로 역추적)

---

## 1. PoC 목표 및 평가 기준

| 목표 | 측정 방법 |
|------|----------|
| 시장 그래프 유사성 | 실제 삼성전자 가격 vs 시뮬레이션 종가 추이 비교 |
| 커뮤니티 효과 측정 | ON/OFF 조건에서 동일 에이전트의 daily 매매 패턴 비교 |
| 에이전트 행동 다양성 | 포지션 변화, 게시글 수, 반응 빈도 분포 |
| 시스템 안정성 | 100명 × 20 거래일 기준 에러율, 완주율 |

---

## 2. 전체 아키텍처 변경 요약

| 항목 | 원본 TwinMarket | 변경 후 PoC |
|------|----------------|------------|
| 종목 | 10개 중국 산업 인덱스 | 삼성전자(005930) 단일 |
| Persona | 1000명 (중국 투자자) | 100명 (행동편향 유지, 시장 맥락 교체) |
| 뉴스 | 중국 A주 거시 뉴스 | 삼성전자 한국어 뉴스 |
| 가격 제한 | ±10% (A주) | ±30% (KRX) |
| 거래 단위 | 100주 | 1주 |
| 커뮤니티 | 항상 ON | ON/OFF 토글 가능 |
| 초기 포지션 | 중국 종목 보유 | 포지션 0 + ini_cash만 보유 |
| 소셜 그래프 | 산업 거래 패턴 기반 | 보유 비율 + Belief 유사도 기반 |

---

## 3. 데이터 플로우 (Community ON vs OFF)

### Community ON
```
[삼성전자 OHLCV + 기술지표]
        │
        ▼
PersonalizedStockTrader
  1. [Forum Action Module]  ◄── forum_db (posts/reactions)
     - 네트워킹 점수 기반 게시글 확률 노출
     - like / repost / unlike
  2. [News Reading] (top_user만)  ◄── samsung_news.pkl (FAISS)
  3. [Stock Recommendation]  ◄── user_graph (NetworkX)
     - Belief + 보유비율 유사도 그래프 이웃 참고
  4. [Belief Update] ← 뉴스 + 포럼 통합
  5. [Trading Decision] LLM → buy / hold / sell
        │
[Matching Engine] → daily_summary.csv
[DB Update] → StockData, Profiles, TradingDetails
[Forum Score Update] → posts.score 갱신
```

### Community OFF
```
[삼성전자 OHLCV + 기술지표]
        │
        ▼
PersonalizedStockTrader
  1. [Forum Action Module] ── SKIP
  2. [News Reading] (top_user만)  ◄── samsung_news.pkl
  3. [Stock Recommendation] ── SKIP (그래프 참고 없음)
  4. [Belief Update] ← 뉴스만 (social input 제거)
  5. [Trading Decision] LLM → buy / hold / sell
        │
[Matching Engine] → daily_summary.csv
[DB Update] → StockData, Profiles, TradingDetails
[Forum Score Update] ── SKIP
```

### ON vs OFF 비교표

| 컴포넌트 | OFF | ON |
|---------|-----|----|
| 뉴스 수신 | top_user만 | top_user만 |
| 포럼 게시글 노출 | ✗ | ✓ 네트워킹 확률 기반 |
| 이웃 포지션 참고 | ✗ | ✓ 그래프 이웃 |
| Belief 입력 소스 | 뉴스만 | 뉴스 + 포럼 |
| 포스트 작성 | ✗ | ✓ |
| 에이전트 거래 자체 | ✓ 정상 | ✓ 정상 |

---

## 4. Block 1 — 초기 상태 리셋

### ini_cash 변환 (위안 → 원)

| 기존 (위안) | 해당 유저 수 | 변환 후 (원) |
|-----------|-----------|------------|
| 1000만 위안 | 731명 | 1억 원 |
| 1억 위안 | 269명 | 10억 원 |

단순 환율 변환이 아닌 **소액투자자 / 대형투자자 티어 비율 유지** 원칙으로 재해석.

### 포지션 완전 초기화

| 필드 | 초기화 값 | 이유 |
|------|---------|------|
| `initial_positions` | `{"005930": 0}` | 삼성전자 관심종목 마커 |
| `cur_positions` | `{}` (빈 dict) | 보유 없음 시작 |
| `stock_returns` | `{}` | 수익률 기록 없음 |
| `yest_returns` | `{}` | 전날 등락 기록 없음 |
| `total_return` | `0` | 누적 수익 초기화 |
| `return_rate` | `0.0` | 수익률 초기화 |
| `total_value` | `= ini_cash` | 현금 = 총자산 |
| `current_cash` | `= ini_cash` | 전액 현금 보유 |

### TradingDetails 처리

- 기존 중국 종목 이력 전체 삭제 (또는 별도 테이블 백업)
- 시뮬레이션 시작 후 삼성전자 거래 이력이 누적되며 그래프 형성

---

## 5. Block 2 — 데이터셋 교체

### 삼성전자 주가 데이터 (stock_data_kr.csv)

StockData 테이블과 동일한 컬럼 포맷 유지:

```
stock_id, date, close_price, pre_close, change, pct_chg,
pe_ttm, pb, ps_ttm, dv_ttm,
vol, vol_5, vol_10, vol_30,
ma_hfq_5, ma_hfq_10, ma_hfq_30,
elg_amount_net
```

- `stock_id`: `005930`
- `elg_amount_net`: 기관+외국인 순매수로 대체
- 수집: `FinanceDataReader` 또는 `pykrx`

### 한국 거래 캘린더 (trading_days_kr.csv)

현재 `trading_days.csv` 컬럼 포맷 유지:
```
cal_date, is_open, pretrade_date
```
KRX 거래일 캘린더 기준.

### 뉴스 데이터 (samsung_news.pkl)

기존 pkl 포맷 동일:
```
DataFrame: cal_date (str) | news (list[str])
```
- 내용: 삼성전자 관련 NAVER Finance 스크래핑
- 임베딩: `paraphrase-multilingual-MiniLM-L12-v2` (한국어 지원 확인됨)

---

## 6. Block 3 — Belief 초기값 수정

### belief_100.csv 현재 구조

```
user_id | belief (LLM 생성 자연어 서술) | attitude (3분류)
```

- `attitude` 비율: 悲观的 50%, 乐观的 40%, 中性 10% → **동일하게 유지**
- `belief` 내용: 중국 A주 → **삼성전자/KOSPI 한국 시장 맥락으로 교체**

### util/init_belief.py 프롬프트 변경 내용

| 항목 | 기존 (중국) | 변경 (한국) |
|------|-----------|-----------|
| 시장 컨텍스트 | 중국 A주 | KOSPI / 삼성전자 |
| 거시 지표 | MLF금리, LPR | 기준금리, 환율(원/달러) |
| 섹터 팩터 | 업종 인덱스 10개 | 반도체 사이클, 메모리 가격 |
| 수익 기준 | 중국 역사적 수익 | 무시 (초기화 상태이므로) |
| 언어 | 중국어 | 한국어 or 영어 (LLM 설정 따름) |

---

## 7. Block 4 — 삼성전자 단일종목 전환

### 강제 거래 조항 제거

현재 `trader/prompts.py:696`, `trader/prompts.py:468`에 박혀 있는 강제 조항:
```
"你必须选择至少一个指数进行buy或者sell类型的交易，否则会受到惩罚"
```
→ 삭제. `hold`도 완전히 유효한 결정으로 허용.

### 거래 단위 변경

`trader/trading_agent.py:239-253`:
```python
# 기존 (100주 단위)
if quantity < 100: quantity = 100
else: quantity = (quantity // 100) * 100

# 변경 (1주 단위)
quantity = max(1, int(quantity))
```

### STOCK_PROFILE_DICT 교체

`trader/utility.py`:
```python
# 기존: 10개 인덱스 딕셔너리
# 변경
STOCK_PROFILE_DICT = {
    "005930": "삼성전자(KRX:005930)는 대한민국 대표 전기전자·반도체 기업이다. KOSPI 시가총액 1위 종목으로, 메모리 반도체(DRAM/NAND), 스마트폰(갤럭시), 디스플레이 사업을 영위한다."
}
```

### fol_ind 교체

모든 유저의 `fol_ind`:
```json
["전기전자", "반도체"]
```

### 다종목 관련 로직 처리

| 항목 | 현재 | 변경 |
|------|------|------|
| 종목 추천 (StockRecommender) | 여러 종목 유사도 기반 | 단일 종목이므로 비활성화 |
| `stocks_to_deal` 리스트 | 2~3개 인덱스 | 항상 `["005930"]` |
| `get_stock_selection_prompt` | 다중 선택 | 단일 종목 고정, LLM 선택 불필요 |

---

## 8. Block 5 — 소셜 네트워크 재설계

### 기존 방식의 문제점

`util/UserDB.py build_graph_new()` 현재 알고리즘:
- **기반**: TradingDetails의 industry 필드로 weighted Jaccard similarity
- **문제**: 모든 유저가 005930 하나만 거래 → industry 동일 → 유사도 균질화 → 의미있는 그래프 불가

### 새로운 네트워킹 기준

**두 유저의 연결 강도 = 포지션 성향 유사도 × 0.5 + Belief 유사도 × 0.5**

```
포지션 성향 유사도:
  - 삼성전자 보유비율(cur_positions["005930"]["ratio"]) 차이의 역수
  - 예: 두 유저가 각각 60%, 62% 보유 → 높은 유사도

Belief 유사도:
  - 각 유저의 최신 belief 텍스트를 동일 임베딩 모델로 벡터화
  - 코사인 유사도로 계산
```

### 글 노출 방식 변경

| 방식 | 기존 | 변경 |
|------|------|------|
| 피드 기본값 | hot score 상위 글 (모든 유저 공통) | hot score 상위 글 (공통 기반 피드) |
| 추가 노출 | 직접 연결 이웃 글만 | 네트워킹 점수에 비례한 확률적 노출 |
| 노이즈 | 없음 | 낮은 연결 강도에도 ε 확률로 노출 |

---

## 9. Block 6 — 커뮤니티 ON/OFF 토글

### 원칙

- **기본값**: `use_community=True` (기존 동작 유지)
- **OFF의 의미**: 에이전트 비활성화 ≠ 커뮤니티 OFF. 거래/뉴스/지표 분석은 계속 동작
- **OFF 시 제거되는 것**: social input (포럼 게시글 읽기, 이웃 포지션 참고, 포스트 작성)
- **OFF 시 유지되는 것**: 뉴스 읽기, 지표 조회, Belief 갱신(뉴스만), 매매 결정

### 영향 받는 코드 위치

| 위치 | 처리 |
|------|------|
| `simulation.py:675` execute_forum_actions | use_community=False면 스킵 |
| `simulation.py:691` update_posts_score_by_date_range | use_community=False면 스킵 |
| `trading_agent.py:541-548` recommend_post_graph | use_community=False면 스킵 |
| `trading_agent.py:915` _intention_agent (게시글 작성) | use_community=False면 스킵 |
| `simulation.py` forum_args 처리 블록 | use_community=False면 스킵 |

---

## 10. 분석 지표 및 실험 설계

### Phase A: 시장 재현성 (거시)
- 실제 삼성전자 주가 vs 시뮬레이션 종가 추이
- Rolling std, Volatility clustering 유무
- 거래량 패턴

### Phase B: 커뮤니티 효과 (미시)

| 분석 항목 | 측정 방법 |
|----------|---------|
| 에이전트별 포지션 변화 | ON vs OFF daily 매매 결정 비교 |
| Belief 수렴 속도 | belief 텍스트 유사도 시계열 |
| 허딩(Herding) 정도 | 특정 날 매수 쏠림 비율 |
| 포럼 활동량 | 게시글 수, 반응 수 시계열 |
| 대형 주문 흐름 | elg_amount_net 분포 |

---

## 11. 미결 사항

- **뉴스 소스**: NAVER Finance 스크래핑 확정
- **초기 그래프**: TradingDetails 없는 초기에는 Belief 유사도만으로 그래프 Seed
- **LLM 언어**: 한국어 sys_prompt 전환 여부
- **기간 선정**: 상승장/하락장/횡보장 중 어느 시기를 선택할지

---

*작성: 2026-05-13 | 상태: Block 1~6 반영 완료*