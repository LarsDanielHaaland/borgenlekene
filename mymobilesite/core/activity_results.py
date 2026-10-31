import random
from dataclasses import dataclass
from django.db import transaction
from django.db.models import Q
from .models import ActivityRanking, Event, Nickname, RunningResult, TennisMatch
from .ranking_writes import RankingIdentity, RankingWriteResult, RunningRankingWriteResult, TennisRankingWriteResult, _replace_ranking, update_total_scores

def update_running_rankings(event):
    with transaction.atomic():
        results = list(RunningResult.objects.filter(event=event).select_related("nickname").order_by("time_seconds", "nickname_id"))
        identity = RankingIdentity(activity_id=4)
        ActivityRanking.objects.filter(event=event, **identity.filter_kwargs()).delete()
        for rank, result in enumerate(results, 1):
            ActivityRanking.objects.create(event=event, nickname=result.nickname, **identity.model_kwargs(), rank=rank)
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
        identity = RankingIdentity(activity_id=1)
        ActivityRanking.objects.filter(
            event=event,
            **identity.filter_kwargs(),
        ).delete()
        for rank, standing in enumerate(standings, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=standing['nickname'],
                **identity.model_kwargs(),
                rank=rank,
            )
        update_total_scores(event)


def randomize_activity_rankings(event, activity_id):
    """Create a random complete ranking for an activity, if participants exist."""
    try:
        identity = RankingIdentity.from_values(activity_id)
    except ValueError:
        return False

    with transaction.atomic():
        nicknames = list(event.nicknames.order_by('id'))
        if not nicknames:
            return False

        random.shuffle(nicknames)
        ActivityRanking.objects.filter(
            event=event,
            **identity.filter_kwargs(),
        ).delete()
        for rank, nickname in enumerate(nicknames, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=nickname,
                **identity.model_kwargs(),
                rank=rank,
            )
        update_total_scores(event)
    return True


@dataclass(frozen=True)
class RankingWriteResult:
    success: bool
    error: str = ""
    created: bool | None = None


@dataclass(frozen=True)
class TennisRankingWriteResult:
    success: bool
    error: str = ""
    created: bool = False


@dataclass(frozen=True)
class RunningRankingWriteResult:
    success: bool
    error: str = ""
    created: bool | None = None


def record_tennis_match(
    event: Event,
    player1_id,
    player2_id,
    winner_id,
) -> TennisRankingWriteResult:
    """Record or update a tennis match and rebuild its ranking outcome."""
    try:
        player1_id = int(player1_id)
        player2_id = int(player2_id)
        winner_id = int(winner_id)
    except (TypeError, ValueError):
        return TennisRankingWriteResult(False, "Player and winner ids must be integers")

    if player1_id == player2_id:
        return TennisRankingWriteResult(False, "A tennis match requires two different players")

    participant_ids = set(
        event.nicknames.filter(
            id__in=(player1_id, player2_id, winner_id)
        ).values_list("id", flat=True)
    )
    if participant_ids != {player1_id, player2_id, winner_id}:
        return TennisRankingWriteResult(False, "All players must belong to this event")
    if winner_id not in {player1_id, player2_id}:
        return TennisRankingWriteResult(False, "Winner must be one of the players")

    player1, player2 = sorted((player1_id, player2_id))
    with transaction.atomic():
        match = TennisMatch.objects.filter(
            event=event,
            player1_id=player1,
            player2_id=player2,
        ).first()
        if match:
            match.winner_id = winner_id
            match.save(update_fields=["winner"])
            created = False
        else:
            TennisMatch.objects.create(
                event=event,
                player1_id=player1,
                player2_id=player2,
                winner_id=winner_id,
            )
            created = True
        update_tennis_rankings(event)

    return TennisRankingWriteResult(True, created=created)


def record_running_time(
    event: Event,
    nickname_id,
    time_seconds,
    group_id=None,
) -> RunningRankingWriteResult:
    """Record or update a running result and rebuild its ranking outcome."""
    try:
        nickname_id = int(nickname_id)
        time_seconds = float(time_seconds)
    except (TypeError, ValueError):
        return RunningRankingWriteResult(False, "Nickname id and time must be valid numbers")

    if time_seconds < 0:
        return RunningRankingWriteResult(False, "Time cannot be negative")

    if not event.nicknames.filter(id=nickname_id).exists():
        return RunningRankingWriteResult(False, "Nickname does not belong to this event")

    with transaction.atomic():
        result, created = RunningResult.objects.update_or_create(
            event=event,
            nickname_id=nickname_id,
            defaults={
                "time_seconds": time_seconds,
                "group_id": group_id,
            },
        )
        update_running_rankings(event)

    return RunningRankingWriteResult(True, created=created)


def delete_running_time(event: Event, nickname_id) -> RunningRankingWriteResult:
    """Delete a running result and rebuild its ranking outcome."""
    try:
        nickname_id = int(nickname_id)
    except (TypeError, ValueError):
        return RunningRankingWriteResult(False, "Nickname id must be an integer")

    with transaction.atomic():
        RunningResult.objects.filter(
            event=event,
            nickname_id=nickname_id,
        ).delete()
        update_running_rankings(event)

    return RunningRankingWriteResult(True)




def save_manual_order(event, activity_id, order, round_num=None):
    try:
        identity = RankingIdentity.from_values(activity_id, round_num)
    except ValueError as error:
        return RankingWriteResult(False, str(error))
    return _replace_ranking(event, identity, order)
