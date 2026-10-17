from enum import Enum

from django.db.models import Q

from .models import Event, Invitation, Nickname

try:
    from allauth.socialaccount.models import SocialAccount
except ImportError:
    SocialAccount = None


class ClaimOutcome(str, Enum):
    CLAIMED = "claimed"
    NOT_INVITED = "not_invited"
    ALREADY_HAS_NICKNAME = "already_has_nickname"
    NICKNAME_UNAVAILABLE = "nickname_unavailable"


def claim_nickname(event: Event, user, nickname: Nickname) -> ClaimOutcome:
    invitations = Invitation.objects.filter(event=event)
    invited = event.owner_id == user.pk
    if not invited:
        invited = not invitations.exists()
    if not invited and user.email:
        invited = invitations.filter(email__iexact=user.email).exists()
    if not invited and SocialAccount is not None:
        has_facebook_account = SocialAccount.objects.filter(
            user=user,
            provider="facebook",
        ).exists()
        if has_facebook_account:
            invited = invitations.filter(
                Q(facebook_profile__isnull=False) & ~Q(facebook_profile="")
            ).exists()

    if not invited:
        return ClaimOutcome.NOT_INVITED

    already_claimed_another_nickname = Nickname.objects.filter(
        event=event,
        user=user,
    ).exclude(pk=nickname.pk).exists()
    if already_claimed_another_nickname:
        return ClaimOutcome.ALREADY_HAS_NICKNAME

    if nickname.user_id is not None and nickname.user_id != user.pk:
        return ClaimOutcome.NICKNAME_UNAVAILABLE

    if nickname.user_id != user.pk:
        nickname.user = user
        nickname.save(update_fields=["user"])

    return ClaimOutcome.CLAIMED
