from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .core import Offer


BASE_URL = "https://www.chemie-brunschwig.ch"
SEARCH_URL = f"{BASE_URL}/actions/search/elastic/search"
DETAIL_URL = f"{BASE_URL}/actions/sapShop/products/get-multiple-item-infos"

QUERY_CONFIG = {
    "disjunctiveFacets": [
        "Name_des_Herstellers",
        "Gruppenname",
        "Verpackungsgruppe",
        "VerkaufsME",
        "Reinheit",
        "Categorie",
        "Listenpreis",
    ],
    "facets": {
        "Name_des_Herstellers": {"type": "value"},
        "Gruppenname": {"type": "value"},
        "Verpackungsgruppe": {"type": "value"},
        "VerkaufsME": {"type": "value"},
        "Reinheit": {"type": "value"},
        "Categorie": {"type": "value"},
        "Listenpreis": {
            "type": "range",
            "ranges": [
                {"from": 0, "to": 50},
                {"from": 50, "to": 100},
                {"from": 100, "to": 500},
                {"from": 500, "to": 1000},
                {"from": 1000},
            ],
        },
    },
}


class BrunschwigClient:
    def __init__(self, page_size: int = 100, timeout: int = 30):
        self.page_size = page_size
        self.timeout = timeout

    def search(self, query: str, exact_cas: bool = False) -> list[Offer]:
        hits: list[dict] = []
        current = 1
        while True:
            filters = []
            if exact_cas:
                filters.append(
                    {"field": "ExactCas", "values": ["true"], "type": "all"}
                )
            payload = {
                "state": {
                    "current": current,
                    "filters": filters,
                    "resultsPerPage": self.page_size,
                    "searchTerm": query,
                },
                "queryConfig": QUERY_CONFIG,
            }
            response = self._post_json(SEARCH_URL, payload)
            page = response.get("results", [])
            hits.extend(page)
            total = int(response.get("totalResults", len(hits)))
            if not page or len(hits) >= total:
                break
            current += 1

        if exact_cas:
            hits = [hit for hit in hits if self._raw(hit, "casnr") == query]

        item_codes = [self._raw(hit, "Artikelnr") for hit in hits]
        item_codes = [code for code in item_codes if code]
        details = self._post_json(DETAIL_URL, {"itemCodes": item_codes}) if item_codes else {}
        return [self._to_offer(hit, details) for hit in hits]

    def _post_json(self, url: str, payload: dict) -> dict:
        request = Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "brunschwig-search/0.1",
                "X-Requested-With": "XMLHttpRequest",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode())

    @staticmethod
    def _raw(hit: dict, key: str, default=None):
        value = hit.get(key, default)
        if isinstance(value, dict) and "raw" in value:
            return value["raw"]
        return value

    def _to_offer(self, hit: dict, details: dict) -> Offer:
        article = str(self._raw(hit, "Artikelnr", ""))
        detail = details.get(article, {})
        description = str(self._raw(hit, "Artikelbeschreibung", ""))
        purity_text = self._raw(hit, "Reinheit") or description
        price = detail.get("Preis", self._raw(hit, "Listenpreis", 0))
        lead_time = detail.get("leadtime", self._raw(hit, "Durchlaufzeit"))
        try:
            lead_time = int(lead_time) if lead_time is not None else None
        except (TypeError, ValueError):
            lead_time = None
        return Offer(
            article=article,
            description=description,
            cas=str(self._raw(hit, "casnr", "")),
            supplier=str(self._raw(hit, "Name_des_Herstellers", "")),
            pack=str(detail.get("packsize") or self._raw(hit, "VerkaufsME", "")),
            purity_text=purity_text,
            price_chf=float(price),
            lead_time_days=lead_time,
        )
