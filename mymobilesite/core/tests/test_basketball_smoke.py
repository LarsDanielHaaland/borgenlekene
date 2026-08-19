from django.test import TestCase, Client
from django.urls import reverse
import json

from core.models import Event, Nickname, ActivityRanking

class BasketballSmokeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name='SmokeTest Basketball Event')
        # create 4 participants
        self.nicknames = [Nickname.objects.create(event=self.event, name=f'P{i}') for i in range(1,5)]

    def test_save_final_order_creates_rankings_and_updates_scores(self):
        # Post a final order to the basketball-prefixed API path
        url = reverse('set_manual_activity_order_basketball_path', kwargs={'pk': self.event.pk})
        order = [n.id for n in self.nicknames]
        payload = {'activity_id': 3, 'order': order}
        resp = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        # There should be ActivityRanking rows for activity_id=3 equal to number of participants
        rankings = ActivityRanking.objects.filter(event=self.event, activity_id=3).order_by('rank')
        self.assertEqual(rankings.count(), len(self.nicknames))

        # Totals: since only one activity has scores, sum of Nickname.total_score should equal triangular number
        total_scores_sum = sum(n.total_score for n in Nickname.objects.filter(event=self.event))
        N = len(self.nicknames)
        expected = N * (N + 1) // 2
        self.assertEqual(total_scores_sum, expected)
