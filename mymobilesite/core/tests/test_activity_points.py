from django.test import TestCase

from ..models import Event, Nickname, ActivityRanking
from ..views.scoring import update_total_scores


class ActivityPointsTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="Activity Points Event")
        # create 6 participants for better coverage
        self.nicknames = [Nickname.objects.create(event=self.event, name=f"Player {i+1}") for i in range(6)]

    def _create_rankings_for_activity(self, activity_id):
        # create a complete ranking 1..N for the given activity
        for rank, nick in enumerate(self.nicknames, start=1):
            ActivityRanking.objects.create(event=self.event, nickname=nick, activity_id=activity_id, rank=rank)

    def test_single_activity_points_match_totals(self):
        """For each activity (tennis, football, running) ensure points sum and participant totals match."""
        activity_ids = [1, 2, 4]  # tennis, football, running
        N = len(self.nicknames)
        expected_triangular = N * (N + 1) // 2

        for activity_id in activity_ids:
            with self.subTest(activity_id=activity_id):
                # clear any existing rankings
                ActivityRanking.objects.filter(event=self.event).delete()
                # create rankings for this activity
                self._create_rankings_for_activity(activity_id)

                # recalc totals
                update_total_scores(self.event)

                # sum points directly from ranking rows
                points_sum = 0
                for ar in ActivityRanking.objects.filter(event=self.event, activity_id=activity_id):
                    points_sum += (N - ar.rank + 1)

                # sum participant total_score
                total_scores_sum = sum(n.total_score for n in Nickname.objects.filter(event=self.event))

                self.assertEqual(points_sum, total_scores_sum)
                self.assertEqual(points_sum, expected_triangular)

    def test_multiple_activities_aggregate_points(self):
        """When multiple activities have rankings, total_score should equal the sum of per-activity points."""
        ActivityRanking.objects.filter(event=self.event).delete()
        # create rankings for tennis (1) and running (4)
        self._create_rankings_for_activity(1)
        self._create_rankings_for_activity(4)

        # recalc totals
        update_total_scores(self.event)

        # expected is sum of two triangular numbers
        N = len(self.nicknames)
        expected = 2 * (N * (N + 1) // 2)

        total_scores_sum = sum(n.total_score for n in Nickname.objects.filter(event=self.event))
        self.assertEqual(total_scores_sum, expected)
