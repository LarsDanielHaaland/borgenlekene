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


@dataclass(frozen=True)
class RankingIdentity:
    """Identify an activity ranking without encoding rounds in activity_id."""

    activity_id: int
    round_number: int | None = None

    @classmethod
    def from_values(cls, activity_id, round_number=None):
        try:
            activity_id = int(activity_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid activity id")

        if round_number is None:
            return cls(activity_id=activity_id)

        try:
            round_number = int(round_number)
        except (TypeError, ValueError):
            raise ValueError("Invalid round value")
        if round_number < 1:
            raise ValueError("Round must be positive")
        return cls(activity_id=activity_id, round_number=round_number)

    def filter_kwargs(self):
        if self.round_number is None:
            return {
                "activity_id": self.activity_id,
                "round_number__isnull": True,
            }
        return {
            "activity_id": self.activity_id,
            "round_number": self.round_number,
        }

    def model_kwargs(self):
        return {
            "activity_id": self.activity_id,
            "round_number": self.round_number,
        }


def ranking_ids(event: Event, identity: RankingIdentity):
    """Return participant ids for one explicit activity ranking identity."""
    rankings = ActivityRanking.objects.filter(
        event=event,
        **identity.filter_kwargs(),
    ).order_by("rank")
    return list(rankings.values_list("nickname_id", flat=True))


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
                round_number__isnull=True,
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
        identity = RankingIdentity(activity_id=4)
        ActivityRanking.objects.filter(
            event=event,
            **identity.filter_kwargs(),
        ).delete()
        for rank, result in enumerate(results, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=result.nickname,
                **identity.model_kwargs(),
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


def save_manual_order(event: Event, activity_id, order, round_num=None) -> RankingWriteResult:
    try:
        identity = RankingIdentity.from_values(activity_id, round_num)
    except ValueError as error:
        return RankingWriteResult(False, str(error))

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
    if set(normalized_order) != valid_ids:
        return RankingWriteResult(
            False,
            "Order must include every event participant exactly once",
        )

    with transaction.atomic():
        ActivityRanking.objects.filter(
            event=event,
            **identity.filter_kwargs(),
        ).delete()
        ActivityRanking.objects.bulk_create([
            ActivityRanking(
                event=event,
                nickname_id=nickname_id,
                **identity.model_kwargs(),
                rank=rank,
            )
            for rank, nickname_id in enumerate(normalized_order, start=1)
        ])
        update_total_scores(event)

    return RankingWriteResult(True)
