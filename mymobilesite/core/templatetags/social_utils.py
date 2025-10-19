from django import template
from allauth.socialaccount.models import SocialApp

register = template.Library()

@register.simple_tag
def social_app_for(provider):
    """Return True if a SocialApp exists for the given provider."""
    try:
        return SocialApp.objects.filter(provider=provider).exists()
    except Exception:
        return False
