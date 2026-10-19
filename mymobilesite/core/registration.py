from collections.abc import Callable
from typing import TypeVar

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Model

from .models import Profile

UserT = TypeVar('UserT', bound=Model)


def validate_display_name(display_name: str) -> str:
    name = display_name.strip()
    if not name:
        raise ValidationError('Visningsnavn kan ikke være tomt.')
    if Profile.objects.filter(display_name__iexact=name).exists():
        raise ValidationError(f"Visningsnavnet '{name}' er allerede tatt.")
    return name


def register_user_with_profile(save_user: Callable[[], UserT], display_name: str) -> UserT:
    name = validate_display_name(display_name)
    with transaction.atomic():
        user = save_user()
        Profile.objects.create(user=user, display_name=name)
    return user
