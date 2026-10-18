from dataclasses import dataclass

from django.db import transaction

from .models import ActivityRanking, Event


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
        from .views.scoring import update_total_scores

        update_total_scores(event)

    return RankingWriteResult(True)
