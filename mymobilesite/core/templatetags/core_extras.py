from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Allows accessing dictionary items with a variable key in templates"""
    return dictionary.get(key)


@register.filter(name='mmss')
def mmss(value):
    """Format seconds (int/float) as M:SS"""
    try:
        total = int(float(value))
    except Exception:
        return value
    mins = total // 60
    secs = total % 60
    return f"{mins}:{secs:02d}"