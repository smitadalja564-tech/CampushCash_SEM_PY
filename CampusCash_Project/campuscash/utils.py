from datetime import date, datetime
import math
import re

def money(value, currency="INR"):
    value = float(value or 0)
    # Indian digit grouping, with two decimal places.
    sign = "-" if value < 0 else ""
    whole, decimals = f"{abs(value):.2f}".split(".")
    if len(whole) > 3:
        last3, rest = whole[-3:], whole[:-3]
        chunks = []
        while len(rest) > 2:
            chunks.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.insert(0, rest)
        whole = ",".join(chunks + [last3])
    symbol = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency, currency + " ")
    return f"{sign}{symbol}{whole}.{decimals}"

def valid_amount(value):
    try:
        amount = float(value)
        return math.isfinite(amount) and amount > 0
    except (TypeError, ValueError):
        return False

def valid_budget(value):
    try:
        amount = float(value)
        return math.isfinite(amount) and amount >= 0
    except (TypeError, ValueError):
        return False

def valid_date(value):
    try:
        if isinstance(value, date):
            return True
        datetime.strptime(str(value), "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False

def month_key(value=None):
    value = value or date.today()
    if isinstance(value, str):
        return value[:7]
    return value.strftime("%Y-%m")

def date_range_sql(start_date, end_date):
    return (str(start_date), str(end_date))
