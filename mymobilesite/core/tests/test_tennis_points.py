from django.test import TestCase

from ..models import Event, Nickname, ActivityRanking
from ..views.scoring import update_total_scores


class TennisPointsTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="Tennis Points Event")
        # create 5 participants
        self.nicknames = []
        for i in range(5):
            n = Nickname.objects.create(event=self.event, name=f"Player {i+1}")
            self.nicknames.append(n)

    def test_tennis_activity_points_sum_matches_participant_totals(self):
        """
        Create a complete ranking for the tennis activity (activity_id=1) and
        verify that the sum of points awarded for that activity equals the sum
        of the participants' total_score after running update_total_scores.

        Points for a single activity are assigned as: points = N - rank + 1
        so the total should equal N*(N+1)/2.
        """
        N = len(self.nicknames)
        # Create ActivityRanking rows for tennis activity (1)
        for rank, nick in enumerate(self.nicknames, start=1):
            ActivityRanking.objects.create(event=self.event, nickname=nick, activity_id=1, rank=rank)

        # Recalculate totals
        update_total_scores(self.event)

        # Sum points from the tennis activity explicitly
        points_sum = 0
        for ar in ActivityRanking.objects.filter(event=self.event, activity_id=1):
            points_sum += (N - ar.rank + 1)

        # Sum participant total_score
        total_scores_sum = sum(n.total_score for n in Nickname.objects.filter(event=self.event))

        # They should match
        self.assertEqual(points_sum, total_scores_sum, "Sum of points from tennis activity must equal sum of participant total_score")
        # And also equal the triangular number
        self.assertEqual(points_sum, N * (N + 1) // 2)
