import json
from unittest.mock import patch

from brunschwig.client import BrunschwigClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def hit(article, price, pack="1KG"):
    return {
        "Artikelnr": {"raw": article},
        "Artikelbeschreibung": {"raw": "Sodium sulfite, 98%, anhydrous"},
        "casnr": {"raw": "7757-83-7"},
        "Name_des_Herstellers": {"raw": "Fluorochem"},
        "VerkaufsME": {"raw": pack},
        "Reinheit": {"raw": "98%"},
        "Listenpreis": {"raw": price},
        "Durchlaufzeit": {"raw": "8"},
    }


def test_search_fetches_all_pages_and_normalizes_hits():
    responses = [
        FakeResponse({"results": [hit("A", 10)], "totalResults": 2}),
        FakeResponse({"results": [hit("B", 20)], "totalResults": 2}),
        FakeResponse(
            {
                "A": {"Preis": 9.5, "leadtime": 3},
                "B": {"Preis": 19.5, "leadtime": 4},
            }
        ),
    ]

    with patch("brunschwig.client.urlopen", side_effect=responses) as mocked:
        offers = BrunschwigClient(page_size=1).search("7757-83-7", exact_cas=True)

    assert mocked.call_count == 3
    assert [item.article for item in offers] == ["A", "B"]
    assert [item.price_chf for item in offers] == [9.5, 19.5]
    assert [item.lead_time_days for item in offers] == [3, 4]


def test_search_uses_description_when_structured_purity_is_missing():
    product = hit("A", 10)
    product["Reinheit"] = {"raw": None}
    responses = [
        FakeResponse({"results": [product], "totalResults": 1}),
        FakeResponse({"A": {"Preis": 10, "leadtime": 8}}),
    ]

    with patch("brunschwig.client.urlopen", side_effect=responses):
        offers = BrunschwigClient().search("7757-83-7", exact_cas=True)

    assert offers[0].purity_text == "Sodium sulfite, 98%, anhydrous"
    assert offers[0].purity == 98.0
