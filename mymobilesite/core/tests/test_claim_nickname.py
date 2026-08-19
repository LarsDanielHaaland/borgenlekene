from django.test import TestCase, Client
from django.urls import reverse

from django.contrib.auth import get_user_model
from core.models import Event, Nickname, Invitation

User = get_user_model()


class ClaimNicknameTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', email='t@test.com', password='pwd')
        self.event = Event.objects.create(name='Claim Event')
        self.nick = Nickname.objects.create(event=self.event, name='PlayerOne')

    def test_claim_nickname_sets_user(self):
        self.client.login(username='tester', password='pwd')
        url = reverse('claim_nickname', kwargs={'pk': self.event.pk, 'nickname_id': self.nick.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.nick.refresh_from_db()
        self.assertEqual(self.nick.user, self.user)

    def test_user_can_have_nicknames_in_multiple_events(self):
        # Claim in first event
        self.client.login(username='tester', password='pwd')
        url = reverse('claim_nickname', kwargs={'pk': self.event.pk, 'nickname_id': self.nick.id})
        self.client.get(url)

        # Create second event and nickname
        e2 = Event.objects.create(name='Event Two')
        n2 = Nickname.objects.create(event=e2, name='PlayerTwo')
        url2 = reverse('claim_nickname', kwargs={'pk': e2.pk, 'nickname_id': n2.id})
        self.client.get(url2)

        n2.refresh_from_db()
        self.assertEqual(n2.user, self.user)
        # user should have two nicknames
        self.assertEqual(self.user.nicknames.count(), 2)

    def test_event_creation_defaults_to_future_status(self):
        self.client.login(username='tester', password='pwd')
        response = self.client.post(reverse('event_create'), {
            'name': 'Auto Status Event',
            'description': 'Created without submitting a status'
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name='Auto Status Event')
        self.assertEqual(event.status, 'future')

    def test_event_creator_can_claim_without_invite(self):
        self.client.login(username='tester', password='pwd')
        create_response = self.client.post(reverse('event_create'), {
            'name': 'Creator Event',
            'description': 'Created by owner'
        })
        self.assertEqual(create_response.status_code, 302)
        event = Event.objects.get(name='Creator Event')
        self.assertEqual(event.owner, self.user)

        nickname = Nickname.objects.create(event=event, name='OwnerPlayer')
        url = reverse('claim_nickname', kwargs={'pk': event.pk, 'nickname_id': nickname.id})
        self.client.get(url)

        nickname.refresh_from_db()
        self.assertEqual(nickname.user, self.user)

    def test_event_list_only_shows_featured_and_user_related_events(self):
        self.client.login(username='tester', password='pwd')

        featured = Event.objects.create(name='Featured Event', status='featured')
        my_event = Event.objects.create(name='My Event', owner=self.user)
        invited_event = Event.objects.create(name='Invited Event')
        Invitation.objects.create(inviter=self.user, event=invited_event, email='t@test.com')
        hidden_event = Event.objects.create(name='Hidden Event')

        response = self.client.get(reverse('event_list'))

        self.assertContains(response, 'Featured Event')
        self.assertContains(response, 'My Event')
        self.assertContains(response, 'Invited Event')
        self.assertNotContains(response, 'Hidden Event')
