from brunschwig.core import (
    Offer,
    Quantity,
    make_order_row,
    parse_pack_size,
    parse_purity,
    parse_quantity,
    rank_offers,
)


def offer(
    article: str,
    pack: str,
    price: float,
    purity: str | None = "98%",
) -> Offer:
    return Offer(
        article=article,
        description="Sodium sulfite, anhydrous",
        cas="7757-83-7",
        supplier="Fluorochem",
        pack=pack,
        purity_text=purity,
        price_chf=price,
        lead_time_days=8,
    )


def test_parse_pack_size_normalizes_mass_and_multipacks():
    assert parse_pack_size("1KG") == Quantity(1000.0, "mass")
    assert parse_pack_size("250GR") == Quantity(250.0, "mass")
    assert parse_pack_size("250 mg") == Quantity(0.25, "mass")
    assert parse_pack_size("4x500GR") == Quantity(2000.0, "mass")
    assert parse_pack_size("4 x 10pk") is None


def test_parse_pack_size_normalizes_volume():
    assert parse_pack_size("100ML") == Quantity(100.0, "volume")
    assert parse_pack_size("2.5 L") == Quantity(2500.0, "volume")


def test_parse_quantity_accepts_cli_units():
    assert parse_quantity("1kg") == Quantity(1000.0, "mass")
    assert parse_quantity("50L") == Quantity(50000.0, "volume")


def test_parse_purity_uses_numeric_lower_bound():
    assert parse_purity("98.5%") == 98.5
    assert parse_purity("99+% (dry basis)") == 99.0
    assert parse_purity(">99.5%") == 99.5
    assert parse_purity(None) is None


def test_rank_offers_finds_cheapest_way_to_cover_requested_mass():
    offers = [
        offer("ONE-KG", "1kg", 21.60),
        offer("TWO-KG", "2kg", 26.90),
        offer("HALF-KG", "500g", 18.90),
        offer("LOW-PURITY", "1kg", 10.00, "97%"),
    ]

    ranked = rank_offers(offers, need=parse_quantity("1.5kg"), min_purity=98)

    assert [item.offer.article for item in ranked] == [
        "TWO-KG",
        "ONE-KG",
        "HALF-KG",
    ]
    assert ranked[0].packs == 1
    assert ranked[0].supplied.amount == 2000.0
    assert ranked[0].total_price_chf == 26.90
    assert ranked[1].packs == 2
    assert ranked[1].total_price_chf == 43.20
    assert ranked[2].packs == 3
    assert ranked[2].total_price_chf == 56.70


def test_rank_without_need_sorts_by_bottle_price():
    ranked = rank_offers(
        [offer("EXPENSIVE", "1kg", 50), offer("CHEAP", "500g", 20)]
    )
    assert [item.offer.article for item in ranked] == ["CHEAP", "EXPENSIVE"]


def test_make_order_row_matches_lab_workbook_columns():
    selected = rank_offers([offer("FLUF044726-1kg", "1kg", 21.60)])[0]
    row = make_order_row(selected, initials="GB", date="24.09.2026")

    assert list(row) == [
        "Date",
        "Product description",
        "Product No.",
        "CAS No.",
        "Supplier",
        "Quantity",
        "Total price CHF",
        "Initials",
        "Order Placed",
        "Arrived",
        "Grant",
    ]
    assert row["Product No."] == "FLUF044726-1kg"
    assert row["Quantity"] == "1kg"
    assert row["Total price CHF"] == 21.60
    assert row["Initials"] == "GB"
    assert row["Order Placed"] == ""
