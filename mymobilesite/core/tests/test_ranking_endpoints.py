import json

from django.test import TestCase
from django.urls import reverse

from core.models import ActivityRanking, Event, Nickname, RunningResult


class RankingEndpointTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="Ranking endpoint event")
        self.first = Nickname.objects.create(event=self.event, name="First")
        self.second = Nickname.objects.create(event=self.event, name="Second")
        self.third = Nickname.objects.create(event=self.event, name="Third")

    def test_record_running_time_updates_result_ranking_and_total(self):
        response = self.client.post(
            reverse("record_running_time", kwargs={"pk": self.event.pk}),
            json.dumps({
                "nickname_id": self.first.pk,
                "time_seconds": 12.5,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "created": True})

        response = self.client.post(
            reverse("record_running_time", kwargs={"pk": self.event.pk}),
            json.dumps({
                "nickname_id": self.second.pk,
                "time_seconds": 9.75,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "created": True})

        rankings = ActivityRanking.objects.filter(
            event=self.event,
            activity_id=4,
        ).order_by("rank")
        self.assertEqual(
            list(rankings.values_list("nickname_id", "rank")),
            [(self.second.pk, 1), (self.first.pk, 2)],
        )
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.third.refresh_from_db()
        self.assertEqual(
            [self.first.total_score, self.second.total_score, self.third.total_score],
            [2, 3, 0],
        )

    def test_deleting_last_running_result_clears_ranks_and_totals(self):
        RunningResult.objects.create(
            event=self.event,
            nickname=self.first,
            time_seconds=8.5,
        )
        ActivityRanking.objects.create(
            event=self.event,
            nickname=self.first,
            activity_id=4,
            rank=1,
        )
        self.first.total_score = 3
        self.first.save(update_fields=["total_score"])

        response = self.client.post(
            reverse("delete_running_time", kwargs={"pk": self.event.pk}),
            json.dumps({"nickname_id": self.first.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.assertFalse(
            RunningResult.objects.filter(
                event=self.event,
                nickname=self.first,
            ).exists()
        )
        self.assertFalse(
            ActivityRanking.objects.filter(
                event=self.event,
                activity_id=4,
            ).exists()
        )
        self.first.refresh_from_db()
        self.assertEqual(self.first.total_score, 0)

    def test_random_ranking_request_keeps_redirect_and_records_every_participant(self):
        response = self.client.post(
            reverse(
                "score_activity",
                kwargs={"pk": self.event.pk, "activity_id": 5},
            ),
        )

        self.assertRedirects(
            response,
            reverse("event_detail", kwargs={"pk": self.event.pk}),
        )
        rankings = ActivityRanking.objects.filter(
            event=self.event,
            activity_id=5,
        ).order_by("rank")
        self.assertEqual(
            set(rankings.values_list("nickname_id", flat=True)),
            {self.first.pk, self.second.pk, self.third.pk},
        )
        self.assertEqual(
            list(rankings.values_list("rank", flat=True)),
            [1, 2, 3],
        )
