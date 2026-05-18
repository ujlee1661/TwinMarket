import json
import math
import random
import shutil
import sqlite3
from collections import Counter
from pathlib import Path


random.seed(42)

DB_PATH = Path("data/sys_100_kr.db")
BACKUP_PATH = Path("data/sys_100_kr_backup.db")
CURRENT_PRICE = 160_500
YEST_RETURN_RATE = 1.2
STOCK_CODE = "005930"

BUCKETS = [
    ("50,000~65,000", 50_000, 65_000, 180),
    ("90,000~110,000", 90_000, 110_000, 120),
    ("120,000~140,000", 120_000, 140_000, 60),
    ("150,000~165,000", 150_000, 165_000, 40),
]


def score_holder(row: dict) -> int:
    score = 0
    if row["bh_total_return_category"] == "高":
        score += 2
    elif row["bh_total_return_category"] == "中":
        score += 1
    if row["bh_underdiversification_category"] == "低":
        score += 1
    if row["bh_annual_turnover_category"] in {"高", "中"}:
        score += 1
    if row["user_type"] in {"大V", "小博主"}:
        score += 1
    return score


def bucket_priority(row: dict) -> tuple[int, int, int, int]:
    low_cost_priority = 0
    if row["bh_disposition_effect_category"] == "高":
        low_cost_priority += 2
    if row["user_type"] in {"大V", "小博主"}:
        low_cost_priority += 1
    if row["bh_total_return_category"] == "高":
        return (1, low_cost_priority, row["score"], -row["rowid"])
    return (0, low_cost_priority, row["score"], -row["rowid"])


def assign_buckets(holders: list[dict]) -> dict[int, tuple[str, int, int]]:
    assignments = {}
    remaining = {row["rowid"]: row for row in holders}

    low_bucket = BUCKETS[0]
    low_candidates = sorted(
        remaining.values(), key=bucket_priority, reverse=True
    )[: low_bucket[3]]
    for row in low_candidates:
        assignments[row["rowid"]] = low_bucket[:3]
        remaining.pop(row["rowid"])

    high_return_rows = [
        row for row in remaining.values() if row["bh_total_return_category"] == "高"
    ]
    random.shuffle(high_return_rows)
    high_return_ids = [row["rowid"] for row in high_return_rows]

    for bucket in BUCKETS[1:]:
        name, low, high, target = bucket
        selected = []

        high_quota = min(len(high_return_ids), max(1, target // 4))
        for _ in range(high_quota):
            rowid = high_return_ids.pop()
            if rowid in remaining:
                selected.append(remaining.pop(rowid))

        if len(selected) < target:
            filler = sorted(
                remaining.values(),
                key=lambda row: (row["score"], -row["rowid"]),
                reverse=True,
            )[: target - len(selected)]
            for row in filler:
                selected.append(remaining.pop(row["rowid"]))

        for row in selected:
            assignments[row["rowid"]] = (name, low, high)

    if len(assignments) != 400:
        raise RuntimeError(f"expected 400 holder assignments, got {len(assignments)}")

    return assignments


def rounded_avg_price(low: int, high: int) -> int:
    raw = random.randint(low, high)
    return int(round(raw / 500) * 500)


def investment_ratio(category: str) -> float:
    if category == "低":
        return random.uniform(0.20, 0.30)
    if category == "高":
        return random.uniform(0.50, 0.70)
    return random.uniform(0.30, 0.50)


def holder_values(row: dict, bucket: tuple[str, int, int]) -> tuple[dict, dict]:
    bucket_name, low, high = bucket
    ini_cash = float(row["ini_cash"])
    avg_price = rounded_avg_price(low, high)
    ratio = investment_ratio(row["bh_underdiversification_category"])
    shares = max(1, math.floor((ini_cash * ratio) / avg_price))

    while shares > 1 and ini_cash - shares * avg_price < 0:
        shares -= 1

    initial_stock_cost = shares * avg_price
    current_cash = ini_cash - initial_stock_cost
    if current_cash < 0:
        raise RuntimeError(f"negative cash for user {row['user_id']}")

    stock_value = shares * CURRENT_PRICE
    total_value = current_cash + stock_value
    total_return = total_value - ini_cash
    return_rate = round(total_return / ini_cash, 4)
    stock_return_rate = round((CURRENT_PRICE - avg_price) / avg_price, 4)
    stock_return_pct = round(stock_return_rate * 100, 1)
    position_ratio = round(stock_value / total_value * 100, 2)

    cur_positions = {STOCK_CODE: {"shares": shares, "ratio": position_ratio}}
    stock_returns = {
        STOCK_CODE: {
            "profit": stock_return_pct,
            "market_value": round(stock_value, 2),
            "stock_return_rate": stock_return_rate,
            "avg_price": avg_price,
        }
    }

    values = {
        "current_cash": round(current_cash, 2),
        "cur_positions": json.dumps(cur_positions, ensure_ascii=False),
        "initial_positions": json.dumps(cur_positions, ensure_ascii=False),
        "total_value": round(total_value, 2),
        "total_return": round(total_return, 2),
        "return_rate": return_rate,
        "stock_returns": json.dumps(stock_returns, ensure_ascii=False),
        "yest_returns": json.dumps({STOCK_CODE: YEST_RETURN_RATE}, ensure_ascii=False),
    }
    summary = {
        "rowid": row["rowid"],
        "user_id": row["user_id"],
        "bucket": bucket_name,
        "avg_price": avg_price,
        "shares": shares,
        "stock_return_rate": stock_return_rate,
    }
    return values, summary


def cash_values(row: dict) -> dict:
    ini_cash = float(row["ini_cash"])
    return {
        "current_cash": round(ini_cash, 2),
        "cur_positions": json.dumps({}, ensure_ascii=False),
        "initial_positions": json.dumps({STOCK_CODE: 0}, ensure_ascii=False),
        "total_value": round(ini_cash, 2),
        "total_return": 0,
        "return_rate": 0.0,
        "stock_returns": json.dumps({}, ensure_ascii=False),
        "yest_returns": json.dumps({}, ensure_ascii=False),
    }


def update_profile(cur: sqlite3.Cursor, row: dict, values: dict) -> None:
    cur.execute(
        """
        UPDATE Profiles
        SET current_cash=?,
            cur_positions=?,
            initial_positions=?,
            total_value=?,
            total_return=?,
            return_rate=?,
            stock_returns=?,
            yest_returns=?
        WHERE rowid=?
        """,
        (
            values["current_cash"],
            values["cur_positions"],
            values["initial_positions"],
            values["total_value"],
            values["total_return"],
            values["return_rate"],
            values["stock_returns"],
            values["yest_returns"],
            row["rowid"],
        ),
    )


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"backup created: {BACKUP_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = [dict(row) for row in cur.execute("SELECT rowid, * FROM Profiles")]
        if len(rows) != 1000:
            raise RuntimeError(f"expected 1000 Profiles rows, got {len(rows)}")

        for row in rows:
            row["score"] = score_holder(row)

        holders = sorted(rows, key=lambda row: (-row["score"], row["rowid"]))[:400]
        holder_ids = {row["rowid"] for row in holders}
        bucket_assignments = assign_buckets(holders)

        holder_summaries = []
        for row in rows:
            if row["rowid"] in holder_ids:
                values, summary = holder_values(row, bucket_assignments[row["rowid"]])
                holder_summaries.append(summary)
            else:
                values = cash_values(row)
            update_profile(cur, row, values)

        conn.commit()

    bucket_counts = Counter(summary["bucket"] for summary in holder_summaries)
    print("holder summary (rowid, user_id, avg_price_bucket, shares, stock_return_rate)")
    for summary in sorted(holder_summaries, key=lambda item: item["rowid"]):
        print(
            summary["rowid"],
            summary["user_id"],
            summary["bucket"],
            summary["shares"],
            summary["stock_return_rate"],
        )
    print(f"cash-only holders: {1000 - len(holder_summaries)}")
    print(f"updated Profiles rows: 1000")
    print("bucket counts:")
    for name, _, _, expected in BUCKETS:
        actual = bucket_counts[name]
        print(f"{name}: {actual}/{expected}")
        if actual != expected:
            raise RuntimeError(f"bucket {name} expected {expected}, got {actual}")


if __name__ == "__main__":
    main()
