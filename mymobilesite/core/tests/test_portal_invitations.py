from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Event, Invitation, Profile


class PortalInvitationTests(TestCase):
    def setUp(self):
        self.inviter = User.objects.create_user(username='inviter', email='inviter@example.com', password='x')
        self.recipient = User.objects.create_user(username='recipient', email='recipient@example.com', password='x')
        Profile.objects.create(user=self.recipient, display_name='CoolRecipient')
        self.event = Event.objects.create(name='Test Event')

    def test_portal_shows_received_invitations_not_sent(self):
        Invitation.objects.create(inviter=self.inviter, event=self.event, email='recipient@example.com')
        Invitation.objects.create(inviter=self.recipient, event=self.event, email='someoneelse@example.com')

        self.client.force_login(self.recipient)
        resp = self.client.get('/portal/')
        self.assertContains(resp, self.event.name)
        # Should show the one invitation received, not the one sent
        self.assertEqual(resp.context['invitations'].count(), 1)
        self.assertEqual(resp.context['invitations'].first().email, 'recipient@example.com')

    def test_portal_matches_invitation_by_display_name(self):
        Invitation.objects.create(inviter=self.inviter, event=self.event, invitee_display_name='coolrecipient')

        self.client.force_login(self.recipient)
        resp = self.client.get('/portal/')
        self.assertEqual(resp.context['invitations'].count(), 1)

    def test_invite_form_rejects_unknown_display_name(self):
        self.client.force_login(self.inviter)
        resp = self.client.post(f'/event/{self.event.pk}/', {
            'invite_submit': '1',
            'display_name': 'NoSuchUser',
        })
        self.assertContains(resp, 'Fant ingen bruker')
