from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from urllib.error import HTTPError, URLError

from .client import BrunschwigClient
from .core import (
    RankedOffer,
    format_quantity,
    make_order_row,
    parse_quantity,
    rank_offers,
)


CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brunschwig",
        description="Search the public Chemie Brunschwig catalogue and rank offers by cost.",
    )
    parser.add_argument("query", help="CAS number, article number or product name")
    parser.add_argument("--need", help="Required amount, for example 250g, 1kg, 500mL or 2L")
    parser.add_argument("--min-purity", type=float, help="Minimum numeric purity percentage")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results to print")
    parser.add_argument(
        "--exact-cas",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Require an exact CAS match; enabled automatically for CAS-shaped queries",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "csv", "order-row"),
        default="table",
    )
    parser.add_argument("--article", help="Article to select for --format order-row")
    parser.add_argument("--initials", default="", help="Initials for an order row")
    parser.add_argument("--grant", default="", help="Grant field for an order row")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        need = parse_quantity(args.need) if args.need else None
        exact_cas = CAS_RE.fullmatch(args.query) is not None
        if args.exact_cas is not None:
            exact_cas = args.exact_cas
        offers = BrunschwigClient().search(args.query, exact_cas=exact_cas)
        ranked = rank_offers(offers, need=need, min_purity=args.min_purity)
    except (ValueError, HTTPError, URLError, TimeoutError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if not ranked:
        print("No compatible offers found.", file=sys.stderr)
        return 1

    ranked = ranked[: max(args.limit, 1)]
    if args.format == "json":
        _print_json(ranked)
    elif args.format == "csv":
        _print_csv(ranked)
    elif args.format == "order-row":
        return _print_order_row(ranked, args.article, args.initials, args.grant)
    else:
        _print_table(ranked, args.query, need)
    return 0


def _print_table(ranked: list[RankedOffer], query: str, need) -> None:
    print(f"Chemie Brunschwig: {query}")
    if need is not None:
        print(f"Need: {format_quantity(need)}. Ranked by total purchase cost.")
    rows = []
    for index, item in enumerate(ranked, start=1):
        offer = item.offer
        lead = f"{offer.lead_time_days} d" if offer.lead_time_days is not None else "unknown"
        purity = offer.purity_text or "unknown"
        supplied = format_quantity(item.supplied)
        rows.append(
            [
                str(index),
                offer.article,
                offer.pack,
                str(item.packs),
                supplied,
                f"CHF {item.total_price_chf:.2f}",
                purity,
                lead,
                offer.supplier,
            ]
        )
    headers = ["#", "Article", "Pack", "Packs", "Supplied", "Total", "Purity", "Lead", "Brand"]
    widths = [max(len(row[i]) for row in [headers, *rows]) for i in range(len(headers))]
    print("  ".join(value.ljust(widths[i]) for i, value in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def _as_dict(item: RankedOffer) -> dict[str, object]:
    return {
        "article": item.offer.article,
        "description": item.offer.description,
        "cas": item.offer.cas,
        "brand": item.offer.supplier,
        "pack": item.offer.pack,
        "packs": item.packs,
        "supplied": format_quantity(item.supplied),
        "purity": item.offer.purity_text,
        "total_price_chf": item.total_price_chf,
        "lead_time_days": item.offer.lead_time_days,
    }


def _print_json(ranked: list[RankedOffer]) -> None:
    print(json.dumps([_as_dict(item) for item in ranked], indent=2, ensure_ascii=False))


def _print_csv(ranked: list[RankedOffer]) -> None:
    rows = [_as_dict(item) for item in ranked]
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)


def _print_order_row(
    ranked: list[RankedOffer],
    article: str | None,
    initials: str,
    grant: str,
) -> int:
    selected = ranked[0]
    if article:
        match = next((item for item in ranked if item.offer.article == article), None)
        if match is None:
            print(f"Article {article!r} is not in the ranked results.", file=sys.stderr)
            return 1
        selected = match
    row = make_order_row(
        selected,
        initials=initials,
        date=date.today().strftime("%d.%m.%Y"),
        grant=grant,
    )
    writer = csv.DictWriter(sys.stdout, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return 0
