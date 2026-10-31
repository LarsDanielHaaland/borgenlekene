import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..ranking_writes import (
    calculate_tennis_standings,
    delete_running_time as delete_running_time_write,
    record_running_time as record_running_time_write,
    record_tennis_match as record_tennis_match_write,
    save_manual_order,
)
from ..models import Event

@require_POST
def record_tennis_match(request, pk):
    """
    Record or update the result of a tennis match using update_or_create.
    This allows changing a winner after a match has been recorded.
    """
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        result = record_tennis_match_write(
            event,
            player1_id=data['player1_id'],
            player2_id=data['player2_id'],
            winner_id=data['winner_id'],
        )
        if not result.success:
            return JsonResponse({'success': False, 'error': result.error})

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
        return JsonResponse({
            'success': True,
            'created': result.created,
            'standings': standings_json,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def record_running_time(request, pk):
    """Record an individual running time for a participant."""
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        result = record_running_time_write(
            event,
            nickname_id=data['nickname_id'],
            time_seconds=data['time_seconds'],
            group_id=data.get('group_id'),
        )
        if not result.success:
            return JsonResponse({'success': False, 'error': result.error})
        return JsonResponse({'success': True, 'created': result.created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def delete_running_time(request, pk):
    """Delete a running result for a participant (used by Reset)."""
    event = get_object_or_404(Event, pk=pk)
    try:
        data = json.loads(request.body)
        result = delete_running_time_write(
            event,
            nickname_id=data['nickname_id'],
        )
        if not result.success:
            return JsonResponse({'success': False, 'error': result.error})

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def set_manual_activity_order(request, pk):
    """Set a manual ordering for an activity (used to break ties).

    Expects JSON: { 'activity_id': int, 'order': [nickname_id, ...] }
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'error': 'Log in to change this event ranking.'},
            status=403,
        )

    event = get_object_or_404(Event, pk=pk)
    is_event_owner = event.owner_id == request.user.pk
    is_claimed_participant = event.nicknames.filter(user_id=request.user.pk).exists()
    if not (is_event_owner or is_claimed_participant):
        return JsonResponse(
            {'success': False, 'error': 'You do not have permission to change this event ranking.'},
            status=403,
        )

    try:
        data = json.loads(request.body)
        result = save_manual_order(
            event,
            activity_id=data.get('activity_id'),
            order=data.get('order', []),
            round_num=data.get('round'),
        )
        if not result.success:
            return JsonResponse({'success': False, 'error': result.error})
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})