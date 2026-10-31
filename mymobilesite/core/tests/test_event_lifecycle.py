from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.event_lifecycle import group_visible_events, status_for
from core.models import Event


class EventLifecycleTests(TestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_status_for_preserves_featured_override(self):
        event = Event.objects.create(
            name="Featured",
            status="featured",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=1),
        )

        self.assertEqual(status_for(event, now=self.now), "featured")
        self.assertEqual(event.get_dynamic_status(), "featured")

    def test_status_for_uses_dates_for_scheduled_events(self):
        future = Event.objects.create(
            name="Future",
            start_date=self.now + timedelta(hours=1),
            end_date=self.now + timedelta(hours=2),
        )
        ongoing = Event.objects.create(
            name="Ongoing",
            start_date=self.now - timedelta(hours=1),
            end_date=self.now + timedelta(hours=1),
        )
        past = Event.objects.create(
            name="Past",
            start_date=self.now - timedelta(hours=2),
            end_date=self.now - timedelta(hours=1),
        )

        self.assertEqual(status_for(future, now=self.now), "future")
        self.assertEqual(status_for(ongoing, now=self.now), "ongoing")
        self.assertEqual(status_for(past, now=self.now), "past")

    def test_group_visible_events_includes_featured_and_user_events(self):
        featured = Event.objects.create(name="Featured", status="featured")
        ongoing = Event.objects.create(
            name="Ongoing",
            start_date=self.now - timedelta(hours=1),
            end_date=self.now + timedelta(hours=1),
        )
        hidden = Event.objects.create(
            name="Hidden",
            start_date=self.now - timedelta(hours=1),
            end_date=self.now + timedelta(hours=1),
        )

        groups = group_visible_events(
            [featured, ongoing, hidden],
            user_event_ids={ongoing.pk},
            now=self.now,
        )

        self.assertEqual(groups["featured_events"], [featured])
        self.assertEqual(groups["ongoing_events"], [ongoing])
        self.assertNotIn(hidden, groups["ongoing_events"])
