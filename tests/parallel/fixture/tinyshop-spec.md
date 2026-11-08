# Spec: tinyshop

> The ids in this file (`FR-NNN`, `BR-NNN`, `VC-NNN`) are this spec's own. They
> are unrelated to the ids of any other document.

## Purpose

`tinyshop` is a small Python library with a command-line front end for the
arithmetic of a toy online shop: pricing a cart, reserving stock, computing
shipping, computing tax and discount, and placing an order. It is written for a
developer who wants a tiny, dependency-free reference shop core that is easy to
read and to extend. Every amount is an integer number of cents.

## Scope

**In**
- Python package `tinyshop`, standard library only, tests with `unittest`.
- Modules: `pricing`, `inventory`, `shipping`, `orders`, `tax`, `discount`, plus
  the `cli` entry point.
- Rates in one TOML file, `tinyshop/rates.toml`.
- Documentation in `docs/` and a README section.

**Out**
- Persistence, networking, currencies other than a single integer-cent unit,
  rounding modes other than floor division, authentication, concurrency.
- Third-party dependencies, packaging to an index, type-checking configuration.
- Combining tax and discount into the order total (they are standalone
  functions in this version).

## Actors

| Actor | Description | Permissions |
|---|---|---|
| Developer | Imports the modules or runs the CLI | Read and run the code, edit rates in `tinyshop/rates.toml` |
| Test runner | `python -m unittest discover` | Import `tinyshop`, read `tinyshop/rates.toml` |

## Functional Requirements

Each of `pricing`, `inventory` and `shipping` is exactly one module and one unit
of work: one source file under `tinyshop/` and one test file under `tests/`,
neither of which needs any other module of the package.

**FR-001 [Must]** Given an empty working directory, when the scaffold is built,
then it contains `pyproject.toml`, the package `tinyshop` (`tinyshop/__init__.py`),
`tests/__init__.py` and `tests/test_smoke.py`, and the smoke test imports
`tinyshop`.

**FR-002 [Must]** Given a cart of `(unit_cents, qty)` pairs, when
`tinyshop.pricing.price_cents(items)` is called, then it returns the sum of
`unit_cents * qty` over all pairs, and `0` for an empty cart. Its tests are in
`tests/test_pricing.py`.

**FR-003 [Must]** Given `Inventory(stock)` where `stock` is a `dict[str, int]`
of sku to units, when `.reserve(sku, n)` is called, then stock for `sku` is
lowered by `n`; if stock for `sku` is less than `n` (or the sku is unknown) it
raises `ValueError` and stock is unchanged. The class is in
`tinyshop/inventory.py`; its tests are in `tests/test_inventory.py`.

**FR-004 [Must]** Given a parcel weight in grams and a zone, when
`tinyshop.shipping.shipping_cents(weight_g, zone)` is called, then the base is
500 for zone `"local"` and 1500 for zone `"intl"`, plus 100 for each full
kilogram of weight; an unknown zone raises `ValueError`. Its tests are in
`tests/test_shipping.py`.

**FR-005 [Must]** Given the three modules above, when `python -m tinyshop.cli`
is run, then these subcommands dispatch to them:
- `price <unit>x<qty> ...` prints the total cents (pricing);
- `stock <have> <want>` builds `Inventory({"x": have})`, reserves `want`, and
  prints `ok`, or prints `insufficient` and exits with status 1 (inventory);
- `ship <weight_g> <zone>` prints the shipping cents (shipping).

**FR-006 [Must]** Given a list of `(sku, unit_cents, qty)` items and an
`Inventory`, when `tinyshop.orders.place(items, inv)` is called, then it
reserves each sku's quantity in `inv`, then returns `price_cents` of the
`(unit_cents, qty)` pairs; if any sku has insufficient stock it raises
`ValueError` and nothing is reserved. `orders` uses `pricing` and `inventory`
and no other module.

**FR-007 [Should]** Given an amount in cents, when
`tinyshop.tax.tax_cents(amount)` is called, then it returns
`amount * tax_bp // 10000`, where `tax_bp` is read from `tinyshop/rates.toml`,
which this requirement creates with the line `tax_bp = 800`. Its tests are in
`tests/test_tax.py`.

**FR-008 [Should]** Given an amount in cents, when
`tinyshop.discount.discount_cents(amount)` is called, then it returns
`amount * discount_bp // 10000`, where `discount_bp` is read from the same
`tinyshop/rates.toml`, to which this requirement adds the line
`discount_bp = 1000`. Its tests are in `tests/test_discount.py`.

**FR-009 [Should]** Given the finished code, when a reader opens the docs, then
`docs/overview.md` and `docs/usage.md` exist and the README has a tinyshop
section; every command shown in `docs/usage.md` runs and prints what the doc
says.

## Business Rules

**BR-001** Money is an integer number of cents everywhere; no function returns
or accepts a float amount. *Rationale*: float rounding errors in money.
*Exceptions*: none.

**BR-002** The code uses only the Python standard library and runs on Python
3.11 or newer. *Rationale*: nothing to install; `tomllib` is available.
*Exceptions*: none.

## Non-Functional Requirements

- **Test speed**: `python -m unittest discover` completes in under 10 seconds on
  a developer laptop with the full suite present.
- **Install footprint**: zero third-party packages are required to import
  `tinyshop` or to run its tests.

## Data & Interfaces

```
pyproject.toml                 # the only manifest
tinyshop/__init__.py           # empty package marker
tinyshop/pricing.py            # price_cents(items: list[tuple[int, int]]) -> int
tinyshop/inventory.py          # class Inventory(stock: dict[str, int]); reserve(sku, n) -> None
tinyshop/shipping.py           # shipping_cents(weight_g: int, zone: str) -> int
tinyshop/orders.py             # place(items: list[tuple[str, int, int]], inv: Inventory) -> int
tinyshop/tax.py                # tax_cents(amount: int) -> int
tinyshop/discount.py           # discount_cents(amount: int) -> int
tinyshop/rates.toml            # tax_bp = 800, discount_bp = 1000
tinyshop/cli.py                # subcommands price, stock, ship
tests/                         # one test file per module, plus test_smoke.py
docs/overview.md, docs/usage.md
```

**Shared files.** These are used by more than one requirement and must not be
edited by two pieces of work at once: `pyproject.toml`, `tinyshop/__init__.py`,
`tinyshop/cli.py`, `tinyshop/rates.toml`, and the `docs/` directory. The modules
`tinyshop/pricing.py`, `tinyshop/inventory.py` and `tinyshop/shipping.py` do not
modify any of them: `tinyshop/__init__.py` stays empty and modules are imported
by their full name (`tinyshop.pricing`). `tinyshop/cli.py` depends on all three
of those modules; `tinyshop/orders.py` depends on pricing and inventory only.

## Verification Criteria

- **VC-001** (FR-001, BR-002): in the scaffold, `python -m unittest discover`
  exits 0 (at least one test exists, as Python 3.12+ exits non-zero when none
  is found), and `python -c "import tinyshop"` exits 0 with nothing installed.
- **VC-002** (FR-002, BR-001): `price_cents([]) == 0` and
  `price_cents([(250, 2)]) == 500`; `python -m unittest tests.test_pricing`
  exits 0.
- **VC-003** (FR-003): `Inventory({"a": 1}).reserve("a", 2)` raises `ValueError`
  and the stock for `"a"` is still 1; `Inventory({"a": 3}).reserve("a", 2)`
  leaves 1; `python -m unittest tests.test_inventory` exits 0.
- **VC-004** (FR-004): `shipping_cents(2500, "local") == 700`;
  `shipping_cents(0, "intl") == 1500`; an unknown zone raises `ValueError`;
  `python -m unittest tests.test_shipping` exits 0.
- **VC-005** (FR-005): `python -m tinyshop.cli price 250x2` prints `500`;
  `python -m tinyshop.cli stock 1 2` prints `insufficient` and exits 1;
  `python -m tinyshop.cli stock 2 1` prints `ok`; `python -m tinyshop.cli ship
  2500 local` prints `700`.
- **VC-006** (FR-006): an order of quantity 2 against stock 1 raises
  `ValueError` and the stock is still 1; a valid order of `[("a", 250, 2)]`
  against stock 5 returns `500` and leaves stock 3.
- **VC-007** (FR-007): `tax_cents(1000) == 80`; loading `tinyshop/rates.toml`
  with `tomllib` gives `tax_bp == 800`; `python -m unittest tests.test_tax`
  exits 0.
- **VC-008** (FR-008): `discount_cents(1000) == 100`; loading
  `tinyshop/rates.toml` with `tomllib` gives `discount_bp == 1000`;
  `python -m unittest tests.test_discount` exits 0.
- **VC-009** (FR-009): `docs/overview.md` and `docs/usage.md` exist; every
  command in `docs/usage.md` run from the repository root prints the documented
  output; the README contains a heading that names tinyshop.
- **VC-010** (end to end, NFR): on the finished repository `python -m unittest
  discover` exits 0 in under 10 seconds with no third-party package installed.

## Open Questions

None.

## Assumptions

- `python` on the developer's `PATH` is Python 3.11 or newer.
- Commands are run from the repository root.
- Floor division (`//`) is the accepted rounding for tax and discount.
