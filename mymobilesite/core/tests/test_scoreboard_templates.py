from django.test import TestCase
from django.urls import reverse

from core.models import Event, Nickname


class SharedScoreboardTemplateTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="Scoreboard test event")
        Nickname.objects.create(event=self.event, name="Ada")
        Nickname.objects.create(event=self.event, name="Linus")

    def get_page(self, route_name):
        return self.client.get(reverse(route_name, kwargs={"pk": self.event.pk}))

    def test_each_game_page_renders_the_shared_scoreboard(self):
        route_names = (
            "tennis_tournament",
            "running_page",
            "football_tournament",
            "basketball_tournament",
            "dice_tournament",
        )

        for route_name in route_names:
            with self.subTest(game=route_name):
                response = self.get_page(route_name)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-scoreboard="true"')
                self.assertContains(response, "Plass")
                self.assertContains(response, "Spiller")

    def test_tournament_pages_share_scoreboards_for_rounds_and_final(self):
        for route_name in ("football_tournament", "basketball_tournament"):
            with self.subTest(game=route_name):
                response = self.get_page(route_name)
                self.assertEqual(response.content.count(b'data-scoreboard="true"'), 4)

    def test_each_game_keeps_its_own_score_columns(self):
        expected_columns = {
            "tennis_tournament": ("Seire", "Tap"),
            "running_page": ("Tid", "Poeng"),
            "football_tournament": ("Poeng", "Total"),
            "basketball_tournament": ("Poeng", "Total"),
            "dice_tournament": (),
        }

        for route_name, labels in expected_columns.items():
            with self.subTest(game=route_name):
                response = self.get_page(route_name)
                for label in labels:
                    self.assertContains(response, label)

    def test_scoreboards_keep_game_specific_move_policies_and_accents(self):
        expected = {
            "tennis_tournament": (1, 0, "#10b981"),
            "running_page": (1, 0, "#0ea5e9"),
            "football_tournament": (1, 3, "#ef4444"),
            "basketball_tournament": (1, 3, "#f59e0b"),
            "dice_tournament": (0, 1, "#ec4899"),
        }

        for route_name, (tie_tables, free_tables, accent) in expected.items():
            with self.subTest(game=route_name):
                response = self.get_page(route_name)
                self.assertEqual(
                    response.content.count(b'data-move-policy="ties"'),
                    tie_tables,
                )
                self.assertEqual(
                    response.content.count(b'data-move-policy="free"'),
                    free_tables,
                )
                self.assertContains(response, f"--scoreboard-accent: {accent}")
