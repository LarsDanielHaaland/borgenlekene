from django.test import TestCase

from core.models import ActivityRanking, Event, Nickname
from core.ranking_writes import save_manual_order


class ManualRankingWriteTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="Ranking write event")
        self.first = Nickname.objects.create(event=self.event, name="First")
        self.second = Nickname.objects.create(event=self.event, name="Second")
        self.saved_ranking = ActivityRanking.objects.create(
            event=self.event,
            nickname=self.first,
            activity_id=2,
            rank=1,
        )

    def test_invalid_nickname_id_keeps_existing_rankings(self):
        result = save_manual_order(
            self.event,
            activity_id=2,
            order=["not-an-id"],
        )

        self.assertFalse(result.success)
        self.assertEqual(
            ActivityRanking.objects.filter(event=self.event, activity_id=2).count(),
            1,
        )
        self.assertTrue(
            ActivityRanking.objects.filter(pk=self.saved_ranking.pk).exists()
        )

    def test_invalid_round_keeps_existing_rankings(self):
        result = save_manual_order(
            self.event,
            activity_id=2,
            order=[self.second.pk],
            round_num="invalid",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid round value")
        self.assertTrue(
            ActivityRanking.objects.filter(pk=self.saved_ranking.pk).exists()
        )

    def test_saves_round_order_with_composite_activity_id(self):
        result = save_manual_order(
            self.event,
            activity_id=2,
            order=[self.second.pk, self.first.pk],
            round_num=3,
        )

        self.assertTrue(result.success)
        rankings = ActivityRanking.objects.filter(
            event=self.event,
            activity_id=23,
        ).order_by("rank")
        self.assertEqual(
            list(rankings.values_list("nickname_id", "rank")),
            [(self.second.pk, 1), (self.first.pk, 2)],
        )

    def test_duplicate_nickname_ids_keep_existing_rankings(self):
        result = save_manual_order(
            self.event,
            activity_id=2,
            order=[self.second.pk, self.second.pk],
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Duplicate nickname ids are not allowed")
        self.assertTrue(
            ActivityRanking.objects.filter(pk=self.saved_ranking.pk).exists()
        )

    def test_empty_order_keeps_existing_rankings(self):
        result = save_manual_order(
            self.event,
            activity_id=2,
            order=[],
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Order must include at least one nickname")
        self.assertTrue(
            ActivityRanking.objects.filter(pk=self.saved_ranking.pk).exists()
        )
