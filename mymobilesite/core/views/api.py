import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from ..models import Event, Nickname, TennisMatch
from ..models import Event, Nickname, TennisMatch, RunningResult
from .scoring import update_total_scores, update_tennis_rankings, calculate_tennis_standings, update_running_rankings

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