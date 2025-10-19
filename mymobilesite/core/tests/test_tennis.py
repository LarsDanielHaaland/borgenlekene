from django.test import TestCase, Client
from django.urls import reverse
import json
from django.contrib.auth import get_user_model

from core.models import Event, Nickname, TennisMatch, ActivityRanking

User = get_user_model()

class TennisMatchTests(TestCase):
    def setUp(self):
        self.client = Client()
        # create user
        self.user = User.objects.create_user(username='tester', password='pass')
        # create event
        self.event = Event.objects.create(name='Test Event')
        # create nicknames
        self.a = Nickname.objects.create(event=self.event, name='Alice')
        self.b = Nickname.objects.create(event=self.event, name='Bob')
        self.c = Nickname.objects.create(event=self.event, name='Charlie')

    def test_canonical_match_creation(self):
        # create match as (a,b)
        m1 = TennisMatch.objects.create(event=self.event, player1=self.a, player2=self.b, winner=self.a)
        # create match with swapped order (b,a) and ensure it doesn't create a duplicate
        m2 = TennisMatch.objects.create(event=self.event, player1=self.b, player2=self.a, winner=self.b)
        matches = TennisMatch.objects.filter(event=self.event)
        # Should be only one match due to canonicalization
        self.assertEqual(matches.count(), 1)
        match = matches.first()
        # Ensure the canonical ordering is player1_id <= player2_id
        self.assertTrue(match.player1.id <= match.player2.id)
        # Winner should be the last saved winner (m2 set winner to b)
        self.assertEqual(match.winner, self.b)

    def test_api_update_updates_correct_match_and_rankings(self):
        # create a match (a,c)
        TennisMatch.objects.create(event=self.event, player1=self.a, player2=self.c, winner=self.a)
        # login
        self.client.login(username='tester', password='pass')
        url = reverse('record_tennis_match', kwargs={'pk': self.event.pk})
        # post result for (c,a) with winner c - should update same match
        payload = {
            'player1_id': self.c.id,
            'player2_id': self.a.id,
            'winner_id': self.c.id,
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        # verify single match exists and winner is c
        matches = TennisMatch.objects.filter(event=self.event)
        self.assertEqual(matches.count(), 1)
        self.assertEqual(matches.first().winner, self.c)
        # standings should reflect 1 win for c
        rankings = ActivityRanking.objects.filter(event=self.event, activity_id=1)
        # There should be 3 rankings (for each player) and winner c should be rank 1
        self.assertTrue(rankings.exists())
        top = rankings.order_by('rank').first()
        self.assertEqual(top.nickname, self.c)
