from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        result = int(value) / int(arg)
        return result
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage of value relative to total."""
    try:
        if int(total) == 0:
            return 0
        return (int(value) / int(total)) * 100
    except (ValueError, TypeError):
        return 0
