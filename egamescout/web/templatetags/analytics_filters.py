from django import template

register = template.Library()

@register.filter
def percentage(value, total):
    if total == 0:
        return 0
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0
