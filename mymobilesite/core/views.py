import random
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.db.models import F, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Event, Nickname, ActivityRanking, TennisMatch
from .forms import EventForm, NicknameForm

def event_list(request):
    """Displays a list of all events."""
    events = Event.objects.all().order_by('-created_at')
    context = {'events': events}
    return render(request, 'core/event_list.html', context)

def event_detail(request, pk):
    """Displays details for a single event, its nicknames, and allows adding nicknames."""
    event = get_object_or_404(Event, pk=pk)
    nicknames = event.nicknames.all()

    if request.method == 'POST':
        form = NicknameForm(request.POST, event=event)
        if form.is_valid():
            try:
                nickname = form.save(commit=False)
                nickname.event = event
                nickname.save()
                messages.success(request, f"Participant '{nickname.name}' added successfully!")
                return redirect('event_detail', pk=event.pk)
            except IntegrityError:
                 messages.error(request, f"Participant '{form.cleaned_data['name']}' already exists.")
            except Exception as e:
                 messages.error(request, f"An unexpected error occurred: {e}")
        else:
            error_list = []
            for field, errors in form.errors.items():
                error_list.append(f"{field}: {', '.join(errors)}")
            messages.error(request, f"Could not add participant. Errors: {'; '.join(error_list)}")
    else:
        form = NicknameForm(event=event)

    # Get existing rankings for each activity
    activity_rankings = {}
    for activity in ACTIVITIES:
        rankings = ActivityRanking.objects.filter(
            event=event, 
            activity_id=activity['id']
        ).select_related('nickname').order_by('rank')
        activity_rankings[activity['id']] = rankings

    context = {
        'event': event,
        'nicknames': nicknames,
        'nickname_form': form,
        'activities': ACTIVITIES,
        'total_participants': nicknames.count(),
        'activity_rankings': activity_rankings,
    }
    return render(request, 'core/event_detail.html', context)

def event_create(request):
    """Handles creation of a new event."""
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            # Optional: Set creator if users are logged in
            # if request.user.is_authenticated:
            #     event.creator = request.user
            event.save()
            messages.success(request, f"Event '{event.name}' created successfully!")
            return redirect(event.get_absolute_url()) # Redirect to the new event's detail page
        else:
             messages.error(request, "Please correct the errors below.")
    else:
        form = EventForm()

    context = {'form': form}
    return render(request, 'core/event_create.html', context)


# --- Scoring Logic ---
ACTIVITIES = [
    {'id': 1, 'name': 'Tennis', 'description': 'Tennis tournament rankings'},
    {'id': 2, 'name': 'Football', 'description': 'Football match performance'},
    {'id': 3, 'name': 'Basketball', 'description': 'Basketball game results'},
    {'id': 4, 'name': 'Running', 'description': 'Running race times'},
    {'id': 5, 'name': 'Dice Game', 'description': 'Dice rolling competition'},
]

def activity_ranking(request, pk, activity_id):
    """Display manual ranking interface for an activity."""
    event = get_object_or_404(Event, pk=pk)
    activity = None
    for act in ACTIVITIES:
        if act['id'] == int(activity_id):
            activity = act
            break
    
    if not activity:
        messages.error(request, "Invalid activity.")
        return redirect('event_detail', pk=event.pk)
    
    nicknames = event.nicknames.all()
    existing_rankings = ActivityRanking.objects.filter(
        event=event, 
        activity_id=activity_id
    ).select_related('nickname').order_by('rank')
    
    # Create a dict for easy lookup
    ranking_dict = {r.nickname.id: r.rank for r in existing_rankings}
    
    context = {
        'event': event,
        'activity': activity,
        'nicknames': nicknames,
        'existing_rankings': existing_rankings,
        'ranking_dict': ranking_dict,
    }
    
    if activity_id == '1':  # Tennis - special tournament view
        return render(request, 'core/tennis_tournament.html', context)
    else:
        return render(request, 'core/manual_ranking.html', context)

@require_POST
def save_activity_ranking(request, pk, activity_id):
    """Save manual rankings for an activity."""
    event = get_object_or_404(Event, pk=pk)
    
    try:
        rankings_data = json.loads(request.body)
        
        with transaction.atomic():
            # Clear existing rankings for this activity
            ActivityRanking.objects.filter(event=event, activity_id=activity_id).delete()
            
            # Save new rankings
            for nickname_id, rank in rankings_data.items():
                nickname = get_object_or_404(Nickname, id=nickname_id, event=event)
                ActivityRanking.objects.create(
                    event=event,
                    nickname=nickname,
                    activity_id=activity_id,
                    rank=rank
                )
            
            # Update total scores
            update_total_scores(event)
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def tennis_tournament(request, pk):
    """Display tennis tournament bracket."""
    event = get_object_or_404(Event, pk=pk)
    nicknames = list(event.nicknames.all())
    
    # Generate all possible matches
    matches = []
    existing_matches = {(m.player1.id, m.player2.id): m for m in TennisMatch.objects.filter(event=event)}
    
    for i, player1 in enumerate(nicknames):
        for j, player2 in enumerate(nicknames):
            if i < j:  # Avoid duplicate matches
                match_key = (player1.id, player2.id)
                reverse_key = (player2.id, player1.id)
                
                if match_key in existing_matches:
                    match = existing_matches[match_key]
                elif reverse_key in existing_matches:
                    match = existing_matches[reverse_key]
                else:
                    match = None
                
                matches.append({
                    'player1': player1,
                    'player2': player2,
                    'match': match
                })
    
    # Calculate current standings
    standings = calculate_tennis_standings(event)
    
    context = {
        'event': event,
        'matches': matches,
        'standings': standings,
        'activity': {'id': 1, 'name': 'Tennis', 'description': 'Tennis tournament'},
    }
    return render(request, 'core/tennis_tournament.html', context)

@require_POST
def record_tennis_match(request, pk):
    """Record the result of a tennis match."""
    event = get_object_or_404(Event, pk=pk)
    
    try:
        data = json.loads(request.body)
        player1_id = data['player1_id']
        player2_id = data['player2_id']
        winner_id = data['winner_id']
        
        player1 = get_object_or_404(Nickname, id=player1_id, event=event)
        player2 = get_object_or_404(Nickname, id=player2_id, event=event)
        winner = get_object_or_404(Nickname, id=winner_id, event=event)
        
        with transaction.atomic():
            # Delete existing match if any
            TennisMatch.objects.filter(
                event=event,
                player1__in=[player1, player2],
                player2__in=[player1, player2]
            ).delete()
            
            # Create new match
            TennisMatch.objects.create(
                event=event,
                player1=player1,
                player2=player2,
                winner=winner
            )
            
            # Update tennis rankings based on wins
            update_tennis_rankings(event)
            # Update total scores
            update_total_scores(event)
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def calculate_tennis_standings(event):
    """Calculate tennis tournament standings based on wins."""
    nicknames = event.nicknames.all()
    standings = []
    
    for nickname in nicknames:
        wins = TennisMatch.objects.filter(event=event, winner=nickname).count()
        total_matches = TennisMatch.objects.filter(
            event=event
        ).filter(
            models.Q(player1=nickname) | models.Q(player2=nickname)
        ).count()
        
        standings.append({
            'nickname': nickname,
            'wins': wins,
            'losses': total_matches - wins,
            'total_matches': total_matches
        })
    
    # Sort by wins (descending), then by losses (ascending)
    standings.sort(key=lambda x: (-x['wins'], x['losses']))
    
    return standings

def update_tennis_rankings(event):
    """Update tennis rankings based on current standings."""
    standings = calculate_tennis_standings(event)
    
    # Clear existing tennis rankings
    ActivityRanking.objects.filter(event=event, activity_id=1).delete()
    
    # Create new rankings
    for rank, standing in enumerate(standings, 1):
        ActivityRanking.objects.create(
            event=event,
            nickname=standing['nickname'],
            activity_id=1,
            rank=rank
        )

def update_total_scores(event):
    """Recalculate total scores for all participants based on activity rankings."""
    nicknames = event.nicknames.all()
    total_participants = nicknames.count()
    
    # Reset all scores
    nicknames.update(total_score=0)
    
    # Add points from each activity
    for activity in ACTIVITIES:
        rankings = ActivityRanking.objects.filter(event=event, activity_id=activity['id'])
        for ranking in rankings:
            points = total_participants - ranking.rank + 1
            ranking.nickname.total_score = F('total_score') + points
            ranking.nickname.save(update_fields=['total_score'])

@require_POST
def score_activity(request, pk, activity_id):
    """Legacy random scoring - redirects to manual ranking."""
    return redirect('activity_ranking', pk=pk, activity_id=activity_id)