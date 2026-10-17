from django.contrib.auth import get_user_model
from django.test import TestCase
from allauth.socialaccount.models import SocialAccount

from core.models import Event, Invitation, Nickname
from core.claiming import ClaimOutcome, claim_nickname


User = get_user_model()


class NicknameClaimOperationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="claimant",
            email="claimant@example.com",
            password="test-password",
        )
        self.event = Event.objects.create(name="Claim operation event")
        self.nickname = Nickname.objects.create(event=self.event, name="Player")

    def test_claims_nickname_when_event_has_no_invitations(self):
        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.CLAIMED)
        self.nickname.refresh_from_db()
        self.assertEqual(self.nickname.user, self.user)

    def test_rejects_user_not_invited_to_event(self):
        inviter = User.objects.create_user(username="inviter", password="test-password")
        Invitation.objects.create(
            inviter=inviter,
            event=self.event,
            email="someone-else@example.com",
        )

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.NOT_INVITED)
        self.nickname.refresh_from_db()
        self.assertIsNone(self.nickname.user)

    def test_rejects_claiming_a_second_nickname_in_the_same_event(self):
        existing_nickname = Nickname.objects.create(
            event=self.event,
            name="Existing player",
            user=self.user,
        )

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.ALREADY_HAS_NICKNAME)
        existing_nickname.refresh_from_db()
        self.nickname.refresh_from_db()
        self.assertEqual(existing_nickname.user, self.user)
        self.assertIsNone(self.nickname.user)

    def test_rejects_nickname_claimed_by_another_user(self):
        other_user = User.objects.create_user(
            username="other-player",
            email="other@example.com",
            password="test-password",
        )
        self.nickname.user = other_user
        self.nickname.save(update_fields=["user"])

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.NICKNAME_UNAVAILABLE)
        self.nickname.refresh_from_db()
        self.assertEqual(self.nickname.user, other_user)

    def test_repeating_same_nickname_claim_is_successful(self):
        self.nickname.user = self.user
        self.nickname.save(update_fields=["user"])

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.CLAIMED)
        self.nickname.refresh_from_db()
        self.assertEqual(self.nickname.user, self.user)

    def test_claims_nickname_when_invited_by_email(self):
        inviter = User.objects.create_user(username="inviter", password="test-password")
        Invitation.objects.create(
            inviter=inviter,
            event=self.event,
            email="CLAIMANT@example.com",
        )

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.CLAIMED)
        self.nickname.refresh_from_db()
        self.assertEqual(self.nickname.user, self.user)

    def test_event_owner_can_claim_when_other_invitations_exist(self):
        self.event.owner = self.user
        self.event.save(update_fields=["owner"])
        inviter = User.objects.create_user(username="inviter", password="test-password")
        Invitation.objects.create(
            inviter=inviter,
            event=self.event,
            email="someone-else@example.com",
        )

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.CLAIMED)
        self.nickname.refresh_from_db()
        self.assertEqual(self.nickname.user, self.user)

    def test_facebook_linked_user_can_claim_when_event_has_facebook_invitation(self):
        SocialAccount.objects.create(
            user=self.user,
            provider="facebook",
            uid="claimant-facebook-id",
        )
        inviter = User.objects.create_user(username="inviter", password="test-password")
        Invitation.objects.create(
            inviter=inviter,
            event=self.event,
            facebook_profile="https://www.facebook.com/invitee-profile",
        )

        outcome = claim_nickname(self.event, self.user, self.nickname)

        self.assertEqual(outcome, ClaimOutcome.CLAIMED)
        self.nickname.refresh_from_db()
        self.assertEqual(self.nickname.user, self.user)
