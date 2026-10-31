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


def _replace_ranking(event, identity, order):
    if not isinstance(order, list): return RankingWriteResult(False, "Order must be a list")
    if not order: return RankingWriteResult(False, "Order must include at least one nickname")
    try: normalized = [int(value) for value in order]
    except (TypeError, ValueError): return RankingWriteResult(False, "Invalid nickname id (not an int): %s" % next((v for v in order if not str(v).lstrip('-').isdigit()), order[0]))
    valid = set(event.nicknames.values_list("id", flat=True))
    invalid = next((value for value in normalized if value not in valid), None)
    if invalid is not None: return RankingWriteResult(False, f"Invalid nickname id: {invalid}")
    if len(normalized) != len(set(normalized)): return RankingWriteResult(False, "Duplicate nickname ids are not allowed")
    if set(normalized) != valid: return RankingWriteResult(False, "Order must include every event participant exactly once")
    with transaction.atomic():
        ActivityRanking.objects.filter(event=event, **identity.filter_kwargs()).delete()
        ActivityRanking.objects.bulk_create([ActivityRanking(event=event, nickname_id=value, **identity.model_kwargs(), rank=rank) for rank, value in enumerate(normalized, 1)])
        update_total_scores(event)
    return RankingWriteResult(True)


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


def calculate_tennis_standings(event):
    from .activity_results import calculate_tennis_standings
    return calculate_tennis_standings(event)

def update_tennis_rankings(event):
    from .activity_results import update_tennis_rankings
    return update_tennis_rankings(event)

def randomize_activity_rankings(event, activity_id):
    from .activity_results import randomize_activity_rankings
    return randomize_activity_rankings(event, activity_id)

def record_tennis_match(event, player1_id, player2_id, winner_id):
    from .activity_results import record_tennis_match
    return record_tennis_match(event, player1_id, player2_id, winner_id)

def record_running_time(event, nickname_id, time_seconds, group_id=None):
    from .activity_results import record_running_time
    return record_running_time(event, nickname_id, time_seconds, group_id)

def delete_running_time(event, nickname_id):
    from .activity_results import delete_running_time
    return delete_running_time(event, nickname_id)

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
