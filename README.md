# Brunschwig Search

A small command-line tool for searching the public Chemie Brunschwig catalogue and comparing the cost of buying enough material for a requested quantity.

Search by CAS number, product name, or article number. Filter by numeric purity, inspect pack sizes and advertised lead times, and export results as a table, JSON, CSV, or a spreadsheet-ready order row.

**Early development.** This is an independent tool, not an official Chemie Brunschwig integration. It reads the public catalogue without a customer login. It does not submit purchases or modify spreadsheets.

## Install

Requires Python 3.11 or newer. There are no third-party runtime dependencies.

```bash
git clone https://github.com/glebo309/brunschwig-search.git
cd brunschwig-search
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
brunschwig --help
```

Alternatively, from a checkout, run `./bin/brunschwig --help` without installing the package. It uses `python3` from your PATH.

## Examples

```bash
# Sodium sulfite: enough for 1.5 kg, with at least 98% stated purity.
brunschwig 7757-83-7 --need 1.5kg --min-purity 98

# Search by product name.
brunschwig 'sodium chloride' --need 500g --limit 5

# Export ranked results for your own scripts or spreadsheet.
brunschwig 7757-83-7 --need 1kg --format json
brunschwig 7757-83-7 --need 1kg --format csv > offers.csv

# Print the cheapest compatible offer as an order row for review.
brunschwig 7757-83-7 --need 1kg --format order-row --initials AB
```

CAS-shaped queries use exact CAS matching automatically. Use `--no-exact-cas` to turn that off, or `--exact-cas` to explicitly require it. The command checks matching, not CAS check digits.

Required amounts accept `mg`, `g`, `kg`, `mL`, and `L`. Mass and volume offers are kept separate; the tool does not infer density. Pack parsing also understands catalogue multipacks such as `4x250g`.

## How ranking works

For each compatible offer, the tool calculates how many identical packs cover the requested amount, then sorts by total purchase price in CHF. Unit price and article number break ties. Without `--need`, it ranks the price of one pack.

For example, using **illustrative prices** and a requirement of 1.5 kg:

| Pack | Price per pack | Packs needed | Amount supplied | Total |
|---|---:|---:|---:|---:|
| 2 kg | CHF 26.90 | 1 | 2 kg | CHF 26.90 |
| 1 kg | CHF 21.60 | 2 | 2 kg | CHF 43.20 |
| 500 g | CHF 18.90 | 3 | 1.5 kg | CHF 56.70 |

It compares repeated packs of each offer independently. It does not optimize a mixed basket of different articles or pack sizes. Offers with unparseable pack sizes or incompatible units are excluded when a required quantity is specified. A purity filter excludes offers without a parseable numeric purity.

## Output and options

| Option | Purpose |
|---|---|
| `--need 250g` | Required amount |
| `--min-purity 98` | Minimum numeric purity percentage |
| `--limit 10` | Maximum offers to display |
| `--exact-cas` / `--no-exact-cas` | Override automatic exact CAS matching |
| `--format table\|json\|csv\|order-row` | Output format |
| `--article ARTICLE` | Select an article for an order row from displayed ranked results |
| `--initials AB` | Optional initials; blank by default |
| `--grant PROJECT` | Optional grant/project field for an order row |

`order-row` emits CSV columns: Date, Product description, Product No., CAS No., Supplier, Quantity, Total price CHF, Initials, Order Placed, Arrived, and Grant. The order/arrival fields remain blank. Increase `--limit` if the article you want is outside the displayed results.

Exit codes: `0` for results, `1` for no compatible offers or an unavailable selected article, `2` for invalid input or a catalogue/network error.

## Limitations

The client uses the website's public search and product-detail endpoints, which can change without notice. Results reflect advertised catalogue data, not a customer-specific quote. It does not calculate shipping, contractual discounts, or a final checkout total. Review the product identity, grade, quantity, availability, and price on the supplier website before ordering.

Unknown catalogue fields may be absent or incomplete. Test coverage uses mocked responses; a passing test suite does not establish that the live catalogue is currently reachable.

## Development

```bash
python -m pip install -e '.[test]'
python -m pytest -q
```

- `src/brunschwig/client.py`: catalogue search, pagination, and product details.
- `src/brunschwig/core.py`: quantity/purity parsing, ranking, and order-row formatting.
- `src/brunschwig/cli.py`: command-line arguments and output formats.
- `tests/`: offline parsing, client, ranking, and CLI tests.

MIT licensed. Contributions and small, reproducible bug reports are welcome.
