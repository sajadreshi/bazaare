"""Sales tax: the rate for a shipping address, and loading the monthly ZIP rate tables.

The shop only charges tax for states it collects in (Admin > Settings > Taxes). The rate
comes from the shipping address's ZIP code in the rate table (loaded from a monthly CSV,
e.g. Avalara's free tables); a ZIP missing from the table uses the state's fallback rate.
Tax is charged on the merchandise, and on shipping where the state taxes shipping (NY does).
"""

import csv
import io
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.extension import db
from app.models import TaxRate, TaxState, utcnow

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class TaxQuote:
    rate: Decimal = Decimal(0)
    state: str | None = None
    region: str | None = None
    tax_shipping: bool = False

    @property
    def applies(self):
        return self.rate > 0

    @property
    def percent(self):
        """The rate as a percentage for display, e.g. "8.625%"."""
        text = f"{self.rate * 100:.3f}".rstrip("0").rstrip(".")
        return f"{text}%"

    def on(self, amount):
        return (Decimal(str(amount or 0)) * self.rate).quantize(CENT, rounding=ROUND_HALF_UP)


NO_TAX = TaxQuote()


def zip5(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:5] if len(digits) >= 5 else None


def quote(address):
    """The sales tax that applies when shipping to ``address`` (NO_TAX if none)."""
    if address is None or not address.state:
        return NO_TAX
    state = db.session.get(TaxState, address.state.strip().upper())
    if state is None or not state.collect:
        return NO_TAX
    code = zip5(address.zip)
    row = db.session.get(TaxRate, code) if code else None
    if row is not None and row.state == state.state:
        return TaxQuote(Decimal(row.rate), state.state, row.region, state.tax_shipping)
    return TaxQuote(
        Decimal(state.fallback_rate or 0), state.state, f"{state.state} (standard rate)", state.tax_shipping
    )


# ---------------------------------------------------------------- loading rate files

# Avalara's free monthly tables use these column names; a simpler "zip,rate" file works too.
COLUMNS = {
    "zip": ("ZipCode", "zip", "Zip", "ZIP"),
    "state": ("State", "state"),
    "region": ("TaxRegionName", "region", "Region"),
    "rate": ("EstimatedCombinedRate", "rate", "Rate", "CombinedRate"),
    "state_rate": ("StateRate",),
    "county_rate": ("EstimatedCountyRate",),
    "city_rate": ("EstimatedCityRate",),
    "special_rate": ("EstimatedSpecialRate",),
}


class RateFileError(Exception):
    pass


def _pick(row, field):
    for name in COLUMNS[field]:
        if name in row and row[name] not in (None, ""):
            return row[name].strip()
    return None


def _rate(value, line):
    try:
        rate = Decimal(value)
    except (InvalidOperation, TypeError) as error:
        raise RateFileError(f"Line {line}: “{value}” isn't a rate.") from error
    if rate > 1:  # written as a percentage, e.g. 8.625
        rate = rate / 100
    if not Decimal(0) <= rate < Decimal("0.5"):
        raise RateFileError(f"Line {line}: {value} doesn't look like a sales tax rate.")
    return rate.quantize(Decimal("0.000001"))


def load_rates(data, source="uploaded file", default_state=None):
    """Replace the ZIP rates for every state in a CSV. Returns {state: number of ZIPs}."""
    text = data.decode("utf-8-sig") if isinstance(data, bytes) else data
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not any(n in reader.fieldnames for n in COLUMNS["zip"]):
        raise RateFileError("The file needs a ZipCode (or zip) column and a rate column.")
    rows = {}
    for line, row in enumerate(reader, start=2):
        code = zip5(_pick(row, "zip"))
        state = (_pick(row, "state") or default_state or "").upper()
        rate = _pick(row, "rate")
        if not code or not rate:
            continue
        if len(state) != 2:
            raise RateFileError(f"Line {line}: no state for ZIP {code}.")
        rows[code] = TaxRate(
            zip=code,
            state=state,
            region=(_pick(row, "region") or "")[:120] or None,
            rate=_rate(rate, line),
            **{
                key: _rate(_pick(row, key), line)
                for key in ("state_rate", "county_rate", "city_rate", "special_rate")
                if _pick(row, key) is not None
            },
        )
    if not rows:
        raise RateFileError("No ZIP codes with rates were found in the file.")
    states = sorted({r.state for r in rows.values()})
    db.session.query(TaxRate).filter(TaxRate.state.in_(states)).delete(synchronize_session=False)
    db.session.query(TaxRate).filter(TaxRate.zip.in_(list(rows))).delete(synchronize_session=False)
    db.session.add_all(rows.values())
    now = utcnow()
    counts = {}
    for state in states:
        setting = db.session.get(TaxState, state)
        if setting is None:
            setting = TaxState(state=state, collect=False, tax_shipping=True, fallback_rate=0)
            db.session.add(setting)
        setting.rates_updated_at = now
        setting.rates_source = source[:200]
        counts[state] = sum(1 for r in rows.values() if r.state == state)
    db.session.flush()
    return counts


def stale_states(days=35):
    """States the shop collects in whose rate table is missing or older than ``days``."""
    from datetime import timedelta

    cutoff = utcnow() - timedelta(days=days)
    return [
        s
        for s in db.session.query(TaxState).filter(TaxState.collect.is_(True)).order_by(TaxState.state)
        if s.rates_updated_at is None or s.rates_updated_at < cutoff
    ]
