import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def register_font() -> str:
    for path in (
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ):
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("ReportFont", path))
            return "ReportFont"
    return "Helvetica"


FONT = register_font()
BASE = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle("title", parent=BASE["Title"], fontName=FONT, fontSize=18, leading=24, spaceAfter=8),
    "h1": ParagraphStyle("h1", parent=BASE["Heading1"], fontName=FONT, fontSize=13, leading=18, spaceBefore=10, spaceAfter=6),
    "body": ParagraphStyle("body", parent=BASE["BodyText"], fontName=FONT, fontSize=9, leading=13, spaceAfter=5),
    "small": ParagraphStyle("small", parent=BASE["BodyText"], fontName=FONT, fontSize=8, leading=11, spaceAfter=3),
}


def p(text, style="body"):
    return Paragraph(str(text).replace("\n", "<br/>"), STYLES[style])


def tbl(rows, widths=None):
    data = [[c if hasattr(c, "wrap") else p(c, "small") for c in row] for row in rows]
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEFF2")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9BEC7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize(root: Path):
    trading_dir = root / "trading_records"
    dates = sorted(path.stem for path in trading_dir.glob("????-??-??.json"))
    rows = []
    totals = {"users": 0, "valid": 0, "buy": 0, "sell": 0, "hold": 0, "orders": 0, "qty": 0}
    for date in dates:
        data = load_json(trading_dir / f"{date}.json")
        actions = {"buy": 0, "sell": 0, "hold": 0}
        valid = 0
        for result in data.values():
            if isinstance(result, dict) and "stock_decisions" in result:
                valid += 1
                for dec in result["stock_decisions"].values():
                    action = dec.get("action")
                    if action in actions:
                        actions[action] += 1
        orders = 0
        qty = 0
        op = trading_dir / f"{date}_orders.json"
        if op.exists():
            order_data = load_json(op)
            for stock_orders in order_data.values():
                for side in ("buy", "sell"):
                    for order in stock_orders.get(side, []):
                        orders += 1
                        qty += int(order.get("quantity", 0))
        rows.append([date, len(data), valid, actions["buy"], actions["sell"], actions["hold"], orders, qty])
        totals["users"] += len(data)
        totals["valid"] += valid
        for k in ("buy", "sell", "hold"):
            totals[k] += actions[k]
        totals["orders"] += orders
        totals["qty"] += qty

    market = []
    for path in sorted((root / "simulation_results").glob("*/daily_summary_*.csv")):
        df = pd.read_csv(path)
        rec = df.iloc[0].to_dict()
        market.append(
            [
                rec.get("date"),
                str(rec.get("stock_code")).zfill(6),
                rec.get("closing_price"),
                rec.get("volume"),
                rec.get("transaction_count"),
                rec.get("large_order_net_inflow"),
            ]
        )

    posts = []
    for path in sorted((root / "post_records").glob("????-??-??.json")):
        data = load_json(path)
        posts.append([path.stem, sum(1 for v in data.values() if isinstance(v, dict) and v)])

    reactions = []
    for path in sorted((root / "reaction_records").glob("????-??-??.json")):
        data = load_json(path)
        count = 0
        for value in data.values():
            if isinstance(value, list):
                count += len(value)
            elif isinstance(value, dict):
                count += 1 if value else 0
            elif value:
                count += 1
        reactions.append([path.stem, count])

    forum_counts = {}
    forum_db = next(root.glob("forum*.db"), None)
    if forum_db:
        with sqlite3.connect(forum_db) as conn:
            for table in ("posts", "reactions", "post_references"):
                try:
                    forum_counts[table] = int(pd.read_sql_query(f"select count(*) as n from {table}", conn).iloc[0]["n"])
                except Exception:
                    forum_counts[table] = 0
    return dates, rows, totals, market, posts, reactions, forum_counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_dir", required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.log_dir)
    dates, rows, totals, market, posts, reactions, forum_counts = summarize(root)
    coverage = f"{totals['valid']}/{totals['users']}" if totals["users"] else "0/0"

    story = [
        p(f"TwinMarket Stage 3 {args.condition} Execution Report", "title"),
        p(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}"),
        p(f"Log directory: {root}"),
        p("Summary", "h1"),
        tbl(
            [
                ["Metric", "Value"],
                ["Date range", f"{dates[0] if dates else 'n/a'} to {dates[-1] if dates else 'n/a'}"],
                ["Completed trading days", len(dates)],
                ["Decision coverage", coverage],
                ["Buy / Sell / Hold", f"{totals['buy']} / {totals['sell']} / {totals['hold']}"],
                ["Generated orders", totals["orders"]],
                ["Generated order quantity", totals["qty"]],
                ["Forum posts", forum_counts.get("posts", sum(v for _, v in posts))],
                ["Forum reactions", forum_counts.get("reactions", sum(v for _, v in reactions))],
                ["Forum repost references", forum_counts.get("post_references", 0)],
            ],
            [55 * mm, 105 * mm],
        ),
        p("Daily Decisions", "h1"),
        tbl([["Date", "Users", "Valid", "Buy", "Sell", "Hold", "Orders", "Qty"]] + rows[:45]),
        p("Market Matching", "h1"),
        tbl([["Date", "Stock", "Close", "Volume", "Transactions", "Large Net Inflow"]] + market[:45]),
        p("Community Records", "h1"),
        tbl([["Date", "Posts"]] + posts[:45]),
        Spacer(1, 5),
        tbl([["Date", "Actions"]] + reactions[:45]),
        p("Notes", "h1"),
        p("The report is generated from existing log artifacts only. Original source data files are not modified by this reporting step."),
    ]

    out = Path(args.output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    doc.build(story)
    print(out)


if __name__ == "__main__":
    main()
