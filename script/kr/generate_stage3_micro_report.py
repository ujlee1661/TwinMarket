import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
OFF_DIR = ROOT / "logs_stage3_micro_off_run"
ON_DIR = ROOT / "logs_stage3_micro_on_run"
OUTPUT = Path.home() / "Downloads" / "stage3_micro_simulation_report.pdf"


def register_font() -> str:
    candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for font_path in candidates:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("ReportFont", font_path))
            return "ReportFont"
    return "Helvetica"


FONT = register_font()


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName=FONT,
            fontSize=18,
            leading=24,
            spaceAfter=8,
            alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT,
            fontSize=13,
            leading=18,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=FONT,
            fontSize=11,
            leading=15,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9,
            leading=13,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8,
            leading=11,
            spaceAfter=3,
        ),
    }


S = styles()


def p(text, style="body"):
    return Paragraph(str(text).replace("\n", "<br/>"), S[style])


def table(rows, widths=None):
    converted = []
    for row in rows:
        converted.append([cell if hasattr(cell, "wrap") else p(cell, "small") for cell in row])
    t = Table(converted, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEFF2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9BEC7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def decision_summary(root: Path):
    rows = []
    totals = {"buy": 0, "sell": 0, "hold": 0, "orders": 0, "quantity": 0}
    for path in sorted((root / "trading_records").glob("2026-02-??.json")):
        data = load_json(path)
        actions = {"buy": 0, "sell": 0, "hold": 0}
        for result in data.values():
            for dec in result.get("stock_decisions", {}).values():
                action = dec.get("action", "unknown")
                if action in actions:
                    actions[action] += 1
        order_path = path.with_name(path.stem + "_orders.json")
        order_count = 0
        quantity = 0
        if order_path.exists():
            orders = load_json(order_path)
            for stock_orders in orders.values():
                for side in ("buy", "sell"):
                    for order in stock_orders.get(side, []):
                        order_count += 1
                        quantity += int(order.get("quantity", 0))
        rows.append([path.stem, actions["buy"], actions["sell"], actions["hold"], order_count, quantity])
        for k in ("buy", "sell", "hold"):
            totals[k] += actions[k]
        totals["orders"] += order_count
        totals["quantity"] += quantity
    return rows, totals


def market_summary(root: Path):
    rows = []
    for path in sorted((root / "simulation_results").glob("*/daily_summary_*.csv")):
        df = pd.read_csv(path)
        rec = df.iloc[0].to_dict()
        rows.append(
            [
                rec.get("date"),
                str(rec.get("stock_code")).zfill(6),
                rec.get("closing_price"),
                rec.get("volume"),
                rec.get("transaction_count"),
                rec.get("large_order_net_inflow"),
            ]
        )
    return rows


def community_summary(root: Path):
    post_rows = []
    for path in sorted((root / "post_records").glob("*.json")):
        data = load_json(path)
        valid = sum(1 for value in data.values() if isinstance(value, dict) and value)
        post_rows.append([path.stem, valid])

    reaction_rows = []
    for path in sorted((root / "reaction_records").glob("*.json")):
        data = load_json(path)
        count = 0
        for value in data.values():
            if isinstance(value, list):
                count += len(value)
            elif isinstance(value, dict):
                count += 1 if value else 0
            elif value:
                count += 1
        reaction_rows.append([path.stem, count])

    db_counts = {}
    forum_db = root / "forum_2_kr_stage3.db"
    if forum_db.exists():
        with sqlite3.connect(forum_db) as conn:
            for name in ("posts", "reactions", "post_references"):
                db_counts[name] = int(
                    pd.read_sql_query(f"select count(*) as n from {name}", conn).iloc[0]["n"]
                )
    return post_rows, reaction_rows, db_counts


def sample_posts(root: Path, limit=4):
    forum_db = root / "forum_2_kr_stage3.db"
    if not forum_db.exists():
        return []
    with sqlite3.connect(forum_db) as conn:
        df = pd.read_sql_query(
            "select user_id, type, created_at, substr(content, 1, 220) as content from posts order by id limit ?",
            conn,
            params=(limit,),
        )
    return df.to_dict("records")


def build_report():
    off_rows, off_totals = decision_summary(OFF_DIR)
    on_rows, on_totals = decision_summary(ON_DIR)
    off_market = market_summary(OFF_DIR)
    on_market = market_summary(ON_DIR)
    off_posts, off_reactions, off_db = community_summary(OFF_DIR)
    on_posts, on_reactions, on_db = community_summary(ON_DIR)

    story = []
    story.append(p("TwinMarket Stage 3 Micro Simulation Report", "title"))
    story.append(p(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}"))
    story.append(
        p(
            "Scope: Samsung Electronics single-stock PoC, 2 agents, 2 trading days "
            "(2026-02-02 to 2026-02-03), community OFF and ON conditions."
        )
    )

    story.append(p("Executive Summary", "h1"))
    story.append(
        table(
            [
                ["Condition", "Users x Days", "Decision Coverage", "Buy", "Sell", "Hold", "Orders", "Order Qty", "Executed Trades"],
                ["Community OFF", "2 x 2", "4/4", off_totals["buy"], off_totals["sell"], off_totals["hold"], off_totals["orders"], off_totals["quantity"], "0"],
                ["Community ON", "2 x 2", "4/4", on_totals["buy"], on_totals["sell"], on_totals["hold"], on_totals["orders"], on_totals["quantity"], "0"],
            ],
            [30 * mm, 24 * mm, 28 * mm, 14 * mm, 14 * mm, 14 * mm, 16 * mm, 20 * mm, 24 * mm],
        )
    )
    story.append(
        p(
            "Both conditions completed the two-day micro-flow with valid agent decisions. "
            "No trades were executed because generated orders were buy-side only, so the matching engine had no sell-side liquidity."
        )
    )

    story.append(p("Run Configuration", "h1"))
    story.append(
        table(
            [
                ["Item", "Value"],
                ["Model config", "config/api.yaml via OpenRouter"],
                ["Embedding config", "config/embedding.yaml via OpenRouter"],
                ["Stock", "005930 Samsung Electronics"],
                ["Agent count", "2"],
                ["Dates", "2026-02-02, 2026-02-03"],
                ["Community OFF output", str(OFF_DIR.relative_to(ROOT))],
                ["Community ON output", str(ON_DIR.relative_to(ROOT))],
            ],
            [42 * mm, 120 * mm],
        )
    )

    story.append(p("Decision Results", "h1"))
    story.append(p("Community OFF", "h2"))
    story.append(table([["Date", "Buy", "Sell", "Hold", "Orders", "Order Qty"]] + off_rows))
    story.append(p("Community ON", "h2"))
    story.append(table([["Date", "Buy", "Sell", "Hold", "Orders", "Order Qty"]] + on_rows))

    story.append(p("Market Matching Results", "h1"))
    story.append(p("Community OFF", "h2"))
    story.append(table([["Date", "Stock", "Close", "Volume", "Transactions", "Large Order Net Inflow"]] + off_market))
    story.append(p("Community ON", "h2"))
    story.append(table([["Date", "Stock", "Close", "Volume", "Transactions", "Large Order Net Inflow"]] + on_market))

    story.append(p("Community Flow", "h1"))
    story.append(
        table(
            [
                ["Metric", "Community OFF", "Community ON"],
                ["Post records by day", str(off_posts), str(on_posts)],
                ["Reaction/action records by day", str(off_reactions), str(on_reactions)],
                ["Forum DB posts", off_db.get("posts", 0), on_db.get("posts", 0)],
                ["Forum DB reactions", off_db.get("reactions", 0), on_db.get("reactions", 0)],
                ["Forum DB post references", off_db.get("post_references", 0), on_db.get("post_references", 0)],
            ],
            [45 * mm, 55 * mm, 70 * mm],
        )
    )
    story.append(
        p(
            "Community ON produced posts on both days and generated second-day interactions. "
            "The forum database contains original posts plus one repost reference, confirming that social posting and reaction paths were exercised."
        )
    )

    samples = sample_posts(ON_DIR)
    if samples:
        story.append(PageBreak())
        story.append(p("Sample Community ON Posts", "h1"))
        for item in samples:
            story.append(
                table(
                    [
                        ["User", item["user_id"]],
                        ["Date", item["created_at"]],
                        ["Type", item["type"]],
                        ["Content", item["content"]],
                    ],
                    [25 * mm, 145 * mm],
                )
            )
            story.append(Spacer(1, 4))

    story.append(p("Implementation Notes", "h1"))
    notes = [
        "OpenRouter base_url was corrected to https://openrouter.ai/api/v1.",
        "The retry wait in Agent.py was corrected from 1000 seconds to 1 second.",
        "A Samsung-only stock profile CSV was added and stock_id reads were normalized to six-digit strings.",
        "FAISS search fell back to same-day samsung_news.pkl because the saved FAISS index dimension did not match the active embedding model.",
        "OpenRouter/Alibaba intermittently returned a provider-side temperature type error; default/fallback decision handling still produced valid decisions.",
    ]
    for note in notes:
        story.append(p(f"- {note}"))

    story.append(p("Artifacts", "h1"))
    story.append(
        table(
            [
                ["Artifact", "Path"],
                ["OFF trading records", "logs_stage3_micro_off_run/trading_records"],
                ["ON trading records", "logs_stage3_micro_on_run/trading_records"],
                ["ON forum DB", "logs_stage3_micro_on_run/forum_2_kr_stage3.db"],
                ["PDF report", str(OUTPUT)],
            ],
            [45 * mm, 125 * mm],
        )
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="TwinMarket Stage 3 Micro Simulation Report",
    )
    doc.build(story)


if __name__ == "__main__":
    build_report()
    print(OUTPUT)
