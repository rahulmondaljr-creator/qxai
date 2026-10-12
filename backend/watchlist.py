"""User-defined watchlist: real Quotex forex pairs only (no OTC)."""

# 19 user-approved pairs, exact display form.
PAIRS = [
    "EUR/JPY", "EUR/USD", "USD/JPY", "AUD/JPY", "CAD/JPY",
    "EUR/GBP", "GBP/USD", "GBP/JPY", "AUD/USD", "AUD/CAD",
    "EUR/AUD", "GBP/AUD", "USD/CHF", "EUR/CAD", "CHF/JPY",
    "GBP/CAD", "USD/CAD", "GBP/CHF", "EUR/CHF", "AUD/CHF",
]

# pyquotex real-market codes use compact form (EUR/USD -> EURUSD).
def to_asset(pair: str) -> str:
    return pair.replace("/", "")


def all_assets() -> list[str]:
    return [to_asset(p) for p in PAIRS]
