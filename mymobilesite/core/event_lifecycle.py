from django.utils import timezone


def status_for(event, now=None):
    """Return one authoritative lifecycle status for an event."""
    if event.status == "featured":
        return "featured"

    now = now or timezone.now()
    if event.start_date and event.end_date:
        if now < event.start_date:
            return "future"
        if now <= event.end_date:
            return "ongoing"
        return "past"
    return event.status


def group_visible_events(events, user_event_ids, now=None):
    """Group visible events by lifecycle status."""
    user_event_ids = set(user_event_ids)
    groups = {
        "featured_events": [],
        "ongoing_events": [],
        "past_events": [],
        "future_events": [],
    }

    for event in events:
        status = status_for(event, now=now)
        if status == "featured":
            groups["featured_events"].append(event)
        elif event.pk in user_event_ids and status in {"ongoing", "past", "future"}:
            groups[f"{status}_events"].append(event)

    return groups
