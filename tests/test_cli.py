from unittest.mock import patch

from brunschwig.cli import main
from brunschwig.core import Offer


def test_cli_prints_cheapest_offer_for_requested_amount(capsys):
    offers = [
        Offer(
            article="FLUF044726-1kg",
            description="Sodium sulfite anhydrous, 98.0%",
            cas="7757-83-7",
            supplier="Fluorochem",
            pack="1kg",
            purity_text="98.0%",
            price_chf=21.60,
            lead_time_days=8,
        )
    ]

    with patch("brunschwig.cli.BrunschwigClient.search", return_value=offers):
        code = main(["7757-83-7", "--need", "1kg"])

    output = capsys.readouterr().out
    assert code == 0
    assert "FLUF044726-1kg" in output
    assert "CHF 21.60" in output
    assert "1 kg" in output


def test_order_row_does_not_insert_developers_initials(capsys):
    import csv
    import io
    offers = [Offer('TEST', 'Example', '7757-83-7', 'Example brand', '1kg', '98%', 20, 8)]
    with patch('brunschwig.cli.BrunschwigClient.search', return_value=offers):
        assert main(['7757-83-7', '--format', 'order-row']) == 0
    row = next(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert row['Initials'] == ''
