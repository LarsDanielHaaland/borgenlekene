from django.test import TestCase, Client
from django.urls import reverse
import json

from core.models import Event, Nickname, ActivityRanking


class FootballApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name='Football API Event')
        # create 4 participants
        self.nicknames = [Nickname.objects.create(event=self.event, name=f'F{i}') for i in range(1,5)]

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


class DiceApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name='Dice API Event')
        # create 5 participants
        self.nicknames = [Nickname.objects.create(event=self.event, name=f'D{i}') for i in range(1,6)]

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
