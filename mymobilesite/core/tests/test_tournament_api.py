from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

from core.models import Event, Nickname, ActivityRanking


class FootballApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = get_user_model().objects.create_user(
            username='football-event-owner',
            password='test-password',
        )
        self.event = Event.objects.create(name='Football API Event', owner=self.owner)
        # create 4 participants
        self.nicknames = [Nickname.objects.create(event=self.event, name=f'F{i}') for i in range(1,5)]
        self.client.force_login(self.owner)

    def test_save_final_order_creates_rankings_and_updates_scores(self):
        url = reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk})
        order = [n.id for n in self.nicknames]
        payload = {'activity_id': 2, 'order': order}
        resp = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        rankings = ActivityRanking.objects.filter(event=self.event, activity_id=2).order_by('rank')
        self.assertEqual(rankings.count(), len(self.nicknames))

        total_scores_sum = sum(n.total_score for n in Nickname.objects.filter(event=self.event))
        N = len(self.nicknames)
        expected = N * (N + 1) // 2
        self.assertEqual(total_scores_sum, expected)

    def test_save_round_order_stores_composite_activity(self):
        # Save a per-round order (round=1) and ensure activity_id stored as 2*10+1 = 21
        url = reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk})
        order = [n.id for n in self.nicknames]
        payload = {'activity_id': 2, 'order': order, 'round': 1}
        resp = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        rankings = ActivityRanking.objects.filter(event=self.event, activity_id=21).order_by('rank')
        self.assertEqual(rankings.count(), len(self.nicknames))

    def test_invalid_order_preserves_saved_ranking_and_returns_error(self):
        existing = ActivityRanking.objects.create(
            event=self.event,
            nickname=self.nicknames[0],
            activity_id=2,
            rank=1,
        )
        url = reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk})

        response = self.client.post(
            url,
            json.dumps({'activity_id': 2, 'order': ['not-an-id']}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'success': False,
            'error': 'Invalid nickname id (not an int): not-an-id',
        })
        self.assertTrue(ActivityRanking.objects.filter(pk=existing.pk).exists())

    def test_empty_order_preserves_saved_ranking(self):
        existing = ActivityRanking.objects.create(
            event=self.event,
            nickname=self.nicknames[0],
            activity_id=2,
            rank=1,
        )

        response = self.client.post(
            reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk}),
            json.dumps({'activity_id': 2, 'order': []}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertTrue(ActivityRanking.objects.filter(pk=existing.pk).exists())

    def test_anonymous_user_cannot_save_manual_order(self):
        existing = ActivityRanking.objects.create(
            event=self.event,
            nickname=self.nicknames[0],
            activity_id=2,
            rank=1,
        )
        self.client.logout()

        response = self.client.post(
            reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk}),
            json.dumps({'activity_id': 2, 'order': [self.nicknames[1].id]}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        self.assertTrue(ActivityRanking.objects.filter(pk=existing.pk).exists())

    def test_unclaimed_user_cannot_save_manual_order(self):
        user = get_user_model().objects.create_user(
            username='unclaimed-user',
            password='test-password',
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk}),
            json.dumps({'activity_id': 2, 'order': [nickname.id for nickname in self.nicknames]}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])

    def test_participant_in_another_event_cannot_save_manual_order(self):
        user = get_user_model().objects.create_user(
            username='other-event-participant',
            password='test-password',
        )
        other_event = Event.objects.create(name='Other event')
        Nickname.objects.create(event=other_event, name='Other participant', user=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk}),
            json.dumps({'activity_id': 2, 'order': [nickname.id for nickname in self.nicknames]}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])

    def test_claimed_event_participant_can_save_manual_order(self):
        participant = get_user_model().objects.create_user(
            username='claimed-participant',
            password='test-password',
        )
        self.nicknames[0].user = participant
        self.nicknames[0].save(update_fields=['user'])
        self.client.force_login(participant)

        response = self.client.post(
            reverse('set_manual_activity_order_football_path', kwargs={'pk': self.event.pk}),
            json.dumps({'activity_id': 2, 'order': [nickname.id for nickname in self.nicknames]}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])


class DiceApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = get_user_model().objects.create_user(
            username='dice-event-owner',
            password='test-password',
        )
        self.event = Event.objects.create(name='Dice API Event', owner=self.owner)
        # create 5 participants
        self.nicknames = [Nickname.objects.create(event=self.event, name=f'D{i}') for i in range(1,6)]
        self.client.force_login(self.owner)

    def test_save_dice_final_awards_equal_distribution(self):
        url = reverse('set_manual_activity_order_dice_path', kwargs={'pk': self.event.pk})
        # Order them so D1 is first
        order = [n.id for n in self.nicknames]
        payload = {'activity_id': 5, 'order': order}
        resp = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        rankings = ActivityRanking.objects.filter(event=self.event, activity_id=5).order_by('rank')
        self.assertEqual(rankings.count(), len(self.nicknames))

        # Total scores should equal the sum of 1..n (same as other activities)
        # With 5 participants: 5+4+3+2+1 = 15
        total_scores_sum = sum(n.total_score for n in Nickname.objects.filter(event=self.event))
        self.assertEqual(total_scores_sum, 15)
