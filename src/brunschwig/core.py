from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Quantity:
    amount: float
    kind: str


@dataclass(frozen=True)
class Offer:
    article: str
    description: str
    cas: str
    supplier: str
    pack: str
    purity_text: str | None
    price_chf: float
    lead_time_days: int | None = None

    @property
    def purity(self) -> float | None:
        return parse_purity(self.purity_text)

    @property
    def pack_quantity(self) -> Quantity | None:
        return parse_pack_size(self.pack)


@dataclass(frozen=True)
class RankedOffer:
    offer: Offer
    packs: int
    supplied: Quantity | None
    total_price_chf: float
    unit_price_chf: float | None


_UNIT_FACTORS = {
    "mg": ("mass", 0.001),
    "g": ("mass", 1.0),
    "gr": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "ml": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "lt": ("volume", 1000.0),
}
_QUANTITY_RE = re.compile(
    r"^\s*(?:(\d+)\s*[x×]\s*)?(\d+(?:[.,]\d+)?)\s*(mg|kg|gr|g|ml|lt|l)\s*$",
    re.IGNORECASE,
)


def parse_pack_size(value: str | None) -> Quantity | None:
    if not value:
        return None
    match = _QUANTITY_RE.match(value)
    if not match:
        return None
    multiplier = int(match.group(1) or 1)
    number = float(match.group(2).replace(",", "."))
    kind, factor = _UNIT_FACTORS[match.group(3).lower()]
    return Quantity(multiplier * number * factor, kind)


def parse_quantity(value: str) -> Quantity:
    quantity = parse_pack_size(value)
    if quantity is None:
        raise ValueError(
            f"Could not parse quantity {value!r}. Use units such as 250g, 1kg, 500mL or 2L."
        )
    return quantity


def parse_purity(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*\+?\s*%", value)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def rank_offers(
    offers: Iterable[Offer],
    need: Quantity | None = None,
    min_purity: float | None = None,
) -> list[RankedOffer]:
    ranked: list[RankedOffer] = []
    for offer in offers:
        purity = offer.purity
        if min_purity is not None and (purity is None or purity < min_purity):
            continue

        pack_quantity = offer.pack_quantity
        packs = 1
        supplied = pack_quantity
        if need is not None:
            if pack_quantity is None or pack_quantity.kind != need.kind:
                continue
            packs = math.ceil(need.amount / pack_quantity.amount)
            supplied = Quantity(pack_quantity.amount * packs, pack_quantity.kind)

        total_price = round(offer.price_chf * packs, 2)
        unit_price = None
        if pack_quantity is not None and pack_quantity.amount > 0:
            unit_price = offer.price_chf / pack_quantity.amount
        ranked.append(
            RankedOffer(
                offer=offer,
                packs=packs,
                supplied=supplied,
                total_price_chf=total_price,
                unit_price_chf=unit_price,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.total_price_chf,
            item.unit_price_chf if item.unit_price_chf is not None else math.inf,
            item.offer.article,
        )
    )
    return ranked


def format_quantity(quantity: Quantity | None) -> str:
    if quantity is None:
        return "unknown"
    if quantity.kind == "mass":
        if quantity.amount >= 1000:
            return f"{quantity.amount / 1000:g} kg"
        if quantity.amount < 1:
            return f"{quantity.amount * 1000:g} mg"
        return f"{quantity.amount:g} g"
    if quantity.amount >= 1000:
        return f"{quantity.amount / 1000:g} L"
    return f"{quantity.amount:g} mL"


def make_order_row(
    selected: RankedOffer,
    initials: str,
    date: str,
    grant: str = "",
) -> dict[str, object]:
    quantity = selected.offer.pack
    if selected.packs > 1:
        quantity = f"{selected.packs} x {selected.offer.pack}"
    return {
        "Date": date,
        "Product description": selected.offer.description,
        "Product No.": selected.offer.article,
        "CAS No.": selected.offer.cas,
        "Supplier": "Chemie-Brunschwig",
        "Quantity": quantity,
        "Total price CHF": selected.total_price_chf,
        "Initials": initials,
        "Order Placed": "",
        "Arrived": "",
        "Grant": grant,
    }
