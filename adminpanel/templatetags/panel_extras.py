from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def tzs(value):
    """12345.5 -> 'TSh 12,346'."""
    if value is None or value == "":
        return "—"
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return value
    return f"TSh {amount:,.0f}"


@register.filter
def absval(value):
    try:
        return abs(value)
    except TypeError:
        return value
