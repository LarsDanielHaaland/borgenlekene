from django.test import TestCase

from core.models import ActivityRanking, Event, Nickname, RunningResult, TennisMatch
from core.ranking_writes import (
    calculate_tennis_standings,
    randomize_activity_rankings,
    update_running_rankings,
    update_tennis_rankings,
)


class RankingGenerationTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="Ranking generation event")
        self.first = Nickname.objects.create(event=self.event, name="First")
        self.second = Nickname.objects.create(event=self.event, name="Second")
        self.third = Nickname.objects.create(event=self.event, name="Third")

    def test_running_results_generate_ordered_rankings_and_totals(self):
        RunningResult.objects.create(
            event=self.event,
            nickname=self.first,
            time_seconds=12.5,
        )
        RunningResult.objects.create(
            event=self.event,
            nickname=self.second,
            time_seconds=9.75,
        )
        RunningResult.objects.create(
            event=self.event,
            nickname=self.third,
            time_seconds=11.0,
        )

        update_running_rankings(self.event)

        rankings = ActivityRanking.objects.filter(
            event=self.event,
            activity_id=4,
        ).order_by("rank")
        self.assertEqual(
            list(rankings.values_list("nickname_id", "rank")),
            [
                (self.second.pk, 1),
                (self.third.pk, 2),
                (self.first.pk, 3),
            ],
        )
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.third.refresh_from_db()
        self.assertEqual(
            [self.first.total_score, self.second.total_score, self.third.total_score],
            [1, 3, 2],
        )

    def test_tennis_standings_generate_rankings_and_totals(self):
        TennisMatch.objects.create(
            event=self.event,
            player1=self.first,
            player2=self.second,
            winner=self.first,
        )
        TennisMatch.objects.create(
            event=self.event,
            player1=self.first,
            player2=self.third,
            winner=self.first,
        )
        TennisMatch.objects.create(
            event=self.event,
            player1=self.second,
            player2=self.third,
            winner=self.third,
        )

        standings = calculate_tennis_standings(self.event)
        self.assertEqual(
            [
                (standing["nickname"].pk, standing["wins"], standing["losses"])
                for standing in standings
            ],
            [
                (self.first.pk, 2, 0),
                (self.third.pk, 1, 1),
                (self.second.pk, 0, 2),
            ],
        )

        update_tennis_rankings(self.event)

        rankings = ActivityRanking.objects.filter(
            event=self.event,
            activity_id=1,
        ).order_by("rank")
        self.assertEqual(
            list(rankings.values_list("nickname_id", "rank")),
            [
                (self.first.pk, 1),
                (self.third.pk, 2),
                (self.second.pk, 3),
            ],
        )
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.third.refresh_from_db()
        self.assertEqual(
            [self.first.total_score, self.second.total_score, self.third.total_score],
            [3, 1, 2],
        )

    def test_random_activity_ranking_covers_each_participant_and_recalculates_totals(self):
        completed = randomize_activity_rankings(self.event, activity_id=5)

        self.assertTrue(completed)
        rankings = ActivityRanking.objects.filter(
            event=self.event,
            activity_id=5,
        ).order_by("rank")
        self.assertEqual(
            set(rankings.values_list("nickname_id", flat=True)),
            set(self.event.nicknames.values_list("pk", flat=True)),
        )
        self.assertEqual(
            list(rankings.values_list("rank", flat=True)),
            [1, 2, 3],
        )
        scores = list(
            self.event.nicknames.order_by("total_score").values_list(
                "total_score",
                flat=True,
            )
        )
        self.assertEqual(scores, [1, 2, 3])
