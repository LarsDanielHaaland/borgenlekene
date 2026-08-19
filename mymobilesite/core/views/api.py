import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from ..models import Event, Nickname, TennisMatch
from ..models import Event, Nickname, TennisMatch, RunningResult
from .scoring import update_total_scores, update_tennis_rankings, calculate_tennis_standings, update_running_rankings
from ..models import ActivityRanking

@require_POST
def record_tennis_match(request, pk):
    """
    Record or update the result of a tennis match using update_or_create.
    This allows changing a winner after a match has been recorded.
    """
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        player1_obj = get_object_or_404(Nickname, id=data['player1_id'], event=event)
        player2_obj = get_object_or_404(Nickname, id=data['player2_id'], event=event)
        winner_obj = get_object_or_404(Nickname, id=data['winner_id'], event=event)

        # Canonicalize ordering by ID
        if player1_obj.id > player2_obj.id:
            player1_obj, player2_obj = player2_obj, player1_obj

        with transaction.atomic():
            # Try to find an existing match with the canonical ordering
            match = TennisMatch.objects.filter(event=event, player1=player1_obj, player2=player2_obj).first()
            if match:
                # Update winner
                match.winner = winner_obj
                match.save()
                created = False
            else:
                match = TennisMatch.objects.create(
                    event=event, player1=player1_obj, player2=player2_obj, winner=winner_obj
                )
                created = True

            # Recalculate rankings and scores
            update_tennis_rankings(event)
            update_total_scores(event)

        # Return success and the updated standings so the client can refresh
        standings = calculate_tennis_standings(event)
        # Simplify standings for JSON: name, wins, losses
        standings_json = [
            {
                'id': s['nickname'].id,
                'name': s['nickname'].name,
                'wins': s['wins'],
                'losses': s['losses']
            }
            for s in standings
        ]
        return JsonResponse({'success': True, 'created': created, 'standings': standings_json})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def record_running_time(request, pk):
    """Record an individual running time for a participant."""
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        nickname = get_object_or_404(Nickname, id=data['nickname_id'], event=event)
        time_seconds = float(data['time_seconds'])
        group_id = data.get('group_id')

        # Create or update the running result for this nickname
        rr, created = RunningResult.objects.update_or_create(
            event=event, nickname=nickname,
            defaults={'time_seconds': time_seconds, 'group_id': group_id}
        )

        # Recalculate running rankings and total scores
        update_running_rankings(event)
        update_total_scores(event)

        return JsonResponse({'success': True, 'created': created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def delete_running_time(request, pk):
    """Delete a running result for a participant (used by Reset)."""
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        nickname = get_object_or_404(Nickname, id=data['nickname_id'], event=event)

        # Delete the running result if it exists
        RunningResult.objects.filter(event=event, nickname=nickname).delete()

        # Recalculate running rankings and total scores
        update_running_rankings(event)
        update_total_scores(event)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def set_manual_activity_order(request, pk):
    """Set a manual ordering for an activity (used to break ties).

    Expects JSON: { 'activity_id': int, 'order': [nickname_id, ...] }
    """
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        activity_id = int(data.get('activity_id'))
        # Optional round parameter to allow storing per-round rankings for
        # multi-round activities (football). When provided we map to a
        # composite activity id so these per-round rankings do not collide
        # with the main activity id used for total scoring.
        round_num = data.get('round')
        if round_num is not None:
            try:
                round_num = int(round_num)
                store_activity_id = activity_id * 10 + round_num
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid round value'})
        else:
            store_activity_id = activity_id
        order = data.get('order', [])

        # Validate nicknames belong to event. The JS may send ids as strings,
        # so coerce to int before validating.
        valid_ids = set(event.nicknames.values_list('id', flat=True))
        normalized_order = []
        for nid in order:
            try:
                nid_int = int(nid)
            except Exception:
                return JsonResponse({'success': False, 'error': f'Invalid nickname id (not an int): {nid}'})
            if nid_int not in valid_ids:
                return JsonResponse({'success': False, 'error': f'Invalid nickname id: {nid_int}'})
            normalized_order.append(nid_int)

        with transaction.atomic():
            # Remove existing rankings for this (possibly composite) activity and write new ones
            ActivityRanking.objects.filter(event=event, activity_id=store_activity_id).delete()
            for rank, nid in enumerate(normalized_order, start=1):
                nick = get_object_or_404(Nickname, id=nid, event=event)
                ActivityRanking.objects.create(event=event, nickname=nick, activity_id=store_activity_id, rank=rank)

            # Recalculate total scores
            update_total_scores(event)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})