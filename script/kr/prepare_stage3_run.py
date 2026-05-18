import argparse
import sqlite3
import shutil
from pathlib import Path


def prepare_user_db(template_db: Path, output_db: Path, node: int, seed_profile_date: str):
    output_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_db, output_db)

    with sqlite3.connect(output_db) as conn:
        cur = conn.cursor()
        users = [
            row[0]
            for row in cur.execute(
                "select distinct user_id from Profiles order by rowid limit ?", (node,)
            ).fetchall()
        ]
        placeholders = ",".join("?" for _ in users)
        for table in ("Profiles", "Strategy", "TradingDetails"):
            cur.execute(f"delete from {table} where user_id not in ({placeholders})", users)
        cur.execute(
            "update Profiles set created_at=? where created_at=?",
            (seed_profile_date, "2023-06-14 00:00:00"),
        )
        conn.commit()

    print(f"prepared {output_db} users={len(users)} seed_profile_date={seed_profile_date}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template_db", default="data/sys_100_kr.db")
    parser.add_argument("--output_db", required=True)
    parser.add_argument("--node", type=int, default=100)
    parser.add_argument("--seed_profile_date", default="2026-02-01 00:00:00")
    args = parser.parse_args()

    prepare_user_db(
        Path(args.template_db),
        Path(args.output_db),
        args.node,
        args.seed_profile_date,
    )


if __name__ == "__main__":
    main()
