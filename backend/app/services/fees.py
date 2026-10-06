from app.config import settings

FEE_FIELDS = ("rent_amount", "agency_fee", "legal_fee", "caution_fee", "other_fees")


def total_move_in_cost(
    rent_amount: int, agency_fee: int = 0, legal_fee: int = 0, caution_fee: int = 0, other_fees: int = 0
) -> int:
    """Everything a renter is asked to pay up front, in whole naira. Always computed server-side."""
    parts = (rent_amount, agency_fee, legal_fee, caution_fee, other_fees)
    if any(p is None or p < 0 for p in parts):
        raise ValueError("Fees must be zero or positive.")
    return sum(parts)


def reservation_deposit(rent_amount: int) -> int:
    """Demo reservation amount: a percentage of annual rent, rounded to the nearest ₦1,000."""
    raw = rent_amount * settings.reservation_deposit_percent / 100
    return max(1000, int(round(raw / 1000.0)) * 1000)
