import random
from dataclasses import dataclass

from django.db import transaction
from django.db.models import F, Q

from .models import (
    ACTIVITIES,
    ActivityRanking,
    Event,
    Nickname,
    RunningResult,
    TennisMatch,
)


def update_total_scores(event):
    """Recalculate total scores for all participants based on activity rankings."""
    with transaction.atomic():
        nicknames = list(event.nicknames.all())
        total_participants = len(nicknames)
        if total_participants == 0:
            return

        Nickname.objects.filter(event=event).update(total_score=0)
        scores_to_add = {nickname.id: 0 for nickname in nicknames}

        for activity in ACTIVITIES:
            rankings = ActivityRanking.objects.filter(
                event=event,
                activity_id=activity['id'],
            )
            for ranking in rankings:
                points = total_participants - ranking.rank + 1
                scores_to_add[ranking.nickname_id] += points

        for nickname_id, points in scores_to_add.items():
            Nickname.objects.filter(pk=nickname_id).update(
                total_score=F('total_score') + points
            )


def update_running_rankings(event):
    """Rebuild running ranks from recorded times and refresh event totals."""
    with transaction.atomic():
        results = list(
            RunningResult.objects.filter(event=event)
            .select_related('nickname')
            .order_by('time_seconds', 'nickname_id')
        )
        ActivityRanking.objects.filter(event=event, activity_id=4).delete()
        for rank, result in enumerate(results, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=result.nickname,
                activity_id=4,
                rank=rank,
            )
        update_total_scores(event)


def calculate_tennis_standings(event):
    """Calculate each participant's tennis wins, losses, and match count."""
    standings = []
    for nickname in event.nicknames.all():
        wins = TennisMatch.objects.filter(event=event, winner=nickname).count()
        total_matches = TennisMatch.objects.filter(event=event).filter(
            Q(player1=nickname) | Q(player2=nickname)
        ).count()
        standings.append({
            'nickname': nickname,
            'wins': wins,
            'losses': total_matches - wins,
            'total_matches': total_matches,
        })
    standings.sort(key=lambda standing: (-standing['wins'], standing['losses']))
    return standings


def update_tennis_rankings(event):
    """Rebuild tennis rankings from match standings and refresh event totals."""
    with transaction.atomic():
        standings = calculate_tennis_standings(event)
        ActivityRanking.objects.filter(event=event, activity_id=1).delete()
        for rank, standing in enumerate(standings, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=standing['nickname'],
                activity_id=1,
                rank=rank,
            )
        update_total_scores(event)


def randomize_activity_rankings(event, activity_id):
    """Create a random complete ranking for an activity, if participants exist."""
    with transaction.atomic():
        nicknames = list(event.nicknames.order_by('id'))
        if not nicknames:
            return False

        random.shuffle(nicknames)
        ActivityRanking.objects.filter(
            event=event,
            activity_id=activity_id,
        ).delete()
        for rank, nickname in enumerate(nicknames, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=nickname,
                activity_id=activity_id,
                rank=rank,
            )
        update_total_scores(event)
    return True


@dataclass(frozen=True)
class RankingWriteResult:
    success: bool
    error: str = ""


def save_manual_order(event: Event, activity_id, order, round_num=None) -> RankingWriteResult:
    try:
        activity_id = int(activity_id)
    except (TypeError, ValueError) as error:
        return RankingWriteResult(False, str(error))

    if round_num is None:
        stored_activity_id = activity_id
    else:
        try:
            stored_activity_id = activity_id * 10 + int(round_num)
        except (TypeError, ValueError):
            return RankingWriteResult(False, "Invalid round value")

    if not isinstance(order, list):
        return RankingWriteResult(False, "Order must be a list")
    if not order:
        return RankingWriteResult(False, "Order must include at least one nickname")

    normalized_order = []
    for nickname_id in order:
        try:
            normalized_id = int(nickname_id)
        except (TypeError, ValueError):
            return RankingWriteResult(
                False,
                f"Invalid nickname id (not an int): {nickname_id}",
            )
        normalized_order.append(normalized_id)

    valid_ids = set(event.nicknames.values_list("id", flat=True))
    for nickname_id in normalized_order:
        if nickname_id not in valid_ids:
            return RankingWriteResult(False, f"Invalid nickname id: {nickname_id}")

    if len(normalized_order) != len(set(normalized_order)):
        return RankingWriteResult(False, "Duplicate nickname ids are not allowed")

    with transaction.atomic():
        ActivityRanking.objects.filter(
            event=event,
            activity_id=stored_activity_id,
        ).delete()
        ActivityRanking.objects.bulk_create([
            ActivityRanking(
                event=event,
                nickname_id=nickname_id,
                activity_id=stored_activity_id,
                rank=rank,
            )
            for rank, nickname_id in enumerate(normalized_order, start=1)
        ])
        update_total_scores(event)

    return RankingWriteResult(True)
