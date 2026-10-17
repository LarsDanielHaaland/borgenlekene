
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction, models
from django.db.models import F

from ..models import Event, Nickname, ActivityRanking, TennisMatch, RunningResult

# --- Scoring Logic ---
ACTIVITIES = [
    {'id': 1, 'name': 'Tennis', 'description': 'Alle møter alle i en sveitsisk-inspirert turnering.'},
    {'id': 4, 'name': 'Running', 'description': 'Finn en bakke og løp til toppen. Raskest tid vinner.'},
    {'id': 2, 'name': 'Football', 'description': 'Straffesparkkonkurranse med utslagsrunder.'},
    {'id': 3, 'name': 'Basketball', 'description': 'Ligaspill over flere runder, poengene summeres.'},
    {'id': 5, 'name': 'Dice Game', 'description': "Terningspill basert på Liar's Dice / Perudo."},
]

def update_total_scores(event):
    """Recalculate total scores for all participants based on activity rankings."""
    nicknames = event.nicknames.all()
    total_participants = nicknames.count()
    if total_participants == 0:
        return


    # Reset all scores
    nicknames.update(total_score=0)

    # Use a dictionary to aggregate points to minimize database writes
    scores_to_add = {nickname.id: 0 for nickname in nicknames}

    # Add points from each activity
    for activity in ACTIVITIES:
        rankings = ActivityRanking.objects.filter(event=event, activity_id=activity['id'])
        for ranking in rankings:
            points = total_participants - ranking.rank + 1
            scores_to_add[ranking.nickname.id] += points

    # Update scores in a single transaction
    with transaction.atomic():
        for nickname_id, points in scores_to_add.items():
            Nickname.objects.filter(pk=nickname_id).update(total_score=F('total_score') + points)


def update_running_rankings(event):
    """Update running rankings based on recorded RunningResult times.

    Lower time is better (rank 1). We write ActivityRanking entries with
    activity_id=4.
    """
    results = list(RunningResult.objects.filter(event=event).select_related('nickname').order_by('time_seconds', 'nickname_id'))
    with transaction.atomic():
        ActivityRanking.objects.filter(event=event, activity_id=4).delete()
        for rank, res in enumerate(results, start=1):
            ActivityRanking.objects.create(
                event=event,
                nickname=res.nickname,
                activity_id=4,
                rank=rank
            )

@require_POST
def score_activity(request, pk, activity_id):
    """Randomly ranks all participants for a given activity."""
    event = get_object_or_404(Event, pk=pk)
    activity_name = next((act['name'] for act in ACTIVITIES if act['id'] == int(activity_id)), "the activity")
    # Use a deterministic ordering for participants so their positions remain
    # static across page reloads and score updates. Order by PK (creation
    # order) which does not change when scores/rankings are updated.
    nicknames = list(event.nicknames.order_by('id').all())

    if not nicknames:
        messages.warning(request, "There are no participants to rank.")
        return redirect('event_detail', pk=pk)

    random.shuffle(nicknames)

    try:
        with transaction.atomic():
            ActivityRanking.objects.filter(event=event, activity_id=activity_id).delete()
            for rank, nickname in enumerate(nicknames, 1):
                ActivityRanking.objects.create(
                    event=event,
                    nickname=nickname,
                    activity_id=activity_id,
                    rank=rank
                )
            update_total_scores(event)
        messages.success(request, f"Successfully randomized rankings for {activity_name}!")
    except Exception as e:
        messages.error(request, f"An error occurred while ranking: {e}")

    return redirect('event_detail', pk=pk)


# --- Tennis Specific Views ---

def calculate_tennis_standings(event):
    """Calculate tennis tournament standings based on wins."""
    standings = []
    for nickname in event.nicknames.all():
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
    standings.sort(key=lambda x: (-x['wins'], x['losses']))
    return standings

def update_tennis_rankings(event):
    """Update tennis rankings based on current standings."""
    standings = calculate_tennis_standings(event)
    with transaction.atomic():
        ActivityRanking.objects.filter(event=event, activity_id=1).delete()
        for rank, standing in enumerate(standings, 1):
            ActivityRanking.objects.create(
                event=event,
                nickname=standing['nickname'],
                activity_id=1,
                rank=rank
            )

def generate_balanced_round_robin(nicknames):
    """
    Generates a balanced round-robin schedule.
    Returns a list of rounds, where each round is a list of matches (player1, player2).
    Handles odd numbers of players by adding a 'bye'.
    """
    if not nicknames:
        return []

    local_nicknames = list(nicknames) # Create a mutable copy

    # If odd number of players, add a dummy "bye" player
    if len(local_nicknames) % 2 != 0:
        local_nicknames.append(None)

    num_players = len(local_nicknames)
    rounds = []
    for _ in range(num_players - 1):
        round_matches = []
        for i in range(num_players // 2):
            player1 = local_nicknames[i]
            player2 = local_nicknames[num_players - 1 - i]
            # Add the match only if it's not a bye
            if player1 is not None and player2 is not None:
                round_matches.append((player1, player2))
        rounds.append(round_matches)
        
        # Rotate players, keeping the first one fixed
        last_player = local_nicknames.pop()
        local_nicknames.insert(1, last_player)

    return rounds


def _build_tournament_scoreboards(participants, accent, accent_dark):
    round_scoreboards = []
    round_columns = [{'key': 'score', 'label': 'Poeng', 'cell_class': 'round-score-cell', 'emphasize': True}]
    for round_number in range(1, 4):
        round_scoreboards.append({
            'table_id': f'round{round_number}-table',
            'table_class': 'table-hover table-sm',
            'header_variant': 'light',
            'move_policy': 'free',
            'accent': accent,
            'accent_dark': accent_dark,
            'round_number': round_number,
            'columns': round_columns,
            'rows': [
                {
                    'id': nickname.id,
                    'name': nickname.name,
                    'rank': index,
                    'metrics': {'score': '-'},
                }
                for index, nickname in enumerate(participants, start=1)
            ],
        })

    final_scoreboard = {
        'table_id': 'final-standing',
        'table_class': '',
        'header_variant': 'accent',
        'move_policy': 'ties',
        'accent': accent,
        'accent_dark': accent_dark,
        'columns': [{'key': 'total', 'label': 'Total', 'cell_class': 'total-cell', 'emphasize': True}],
        'rows': [
            {
                'id': nickname.id,
                'name': nickname.name,
                'rank': index,
                'metrics': {'total': '-'},
            }
            for index, nickname in enumerate(participants, start=1)
        ],
    }
    return round_scoreboards, final_scoreboard

def tennis_tournament(request, pk):
    """
    Display tennis tournament pairings (round-robin), standings,
    and check if the tournament is concluded.
    """
    event = get_object_or_404(Event, pk=pk)
    nicknames = list(event.nicknames.all())
    num_nicknames = len(nicknames)

    # --- Round Robin Logic (balanced) ---
    matches_to_play = []
    # Use a dictionary to quickly look up existing matches keyed by sorted ids
    existing_matches = {
        tuple(sorted((m.player1.id, m.player2.id))): m
        for m in TennisMatch.objects.filter(event=event).select_related('winner', 'player1', 'player2')
    }

    # If enough players, generate a balanced round-robin schedule so matches
    # are spread across rounds instead of one player playing all matches first.
    if num_nicknames >= 2:
        rounds = generate_balanced_round_robin(nicknames)
        for round_index, round_matches in enumerate(rounds, start=1):
            for player1, player2 in round_matches:
                match_key = tuple(sorted((player1.id, player2.id)))
                matches_to_play.append({
                    'round': round_index,
                    'player1': player1,
                    'player2': player2,
                    'match': existing_matches.get(match_key)
                })

    # --- Check if Concluded ---
    total_possible_matches = (num_nicknames * (num_nicknames - 1)) // 2 if num_nicknames >= 2 else 0
    played_matches_count = len(existing_matches)
    is_concluded = total_possible_matches > 0 and played_matches_count == total_possible_matches

    standings = calculate_tennis_standings(event)
    context = {
        'event': event,
        'matches': matches_to_play,
        'standings': standings,
        'scoreboard': {
            'table_id': 'final-standing',
            'table_class': '',
            'header_variant': 'accent',
            'move_policy': 'ties',
            'accent': '#10b981',
            'accent_dark': '#059669',
            'columns': [
                {'key': 'wins', 'label': 'Seire', 'cell_class': 'wins-cell', 'emphasize': True},
                {'key': 'losses', 'label': 'Tap', 'cell_class': 'losses-cell'},
            ],
            'rows': [
                {
                    'id': standing['nickname'].id,
                    'name': standing['nickname'].name,
                    'rank': index,
                    'tie_value': standing['wins'],
                    'metrics': {
                        'wins': standing['wins'],
                        'losses': standing['losses'],
                    },
                }
                for index, standing in enumerate(standings, start=1)
            ],
        },
        'activity': {'id': 1, 'name': 'Tennis'}, # Pass activity info
        'is_concluded': is_concluded,
        'total_participants': num_nicknames
    }
    return render(request, 'core/tennis_tournament.html', context)


def running_page(request, pk):
    """Render the running page with participants and any existing running results."""
    event = get_object_or_404(Event, pk=pk)
    nicknames = list(event.nicknames.order_by('id').all())
    # Load existing running results keyed by nickname id
    existing = {r.nickname_id: r for r in RunningResult.objects.filter(event=event)}

    participants = []
    for n in nicknames:
        participants.append({
            'nickname': n,
            'result': existing.get(n.id)
        })

    result_rows = [participant for participant in participants if participant['result']]
    total_results = len(result_rows)
    scoreboard_rows = []
    for rank, participant in enumerate(result_rows, start=1):
        seconds = int(float(participant['result'].time_seconds))
        scoreboard_rows.append({
            'id': participant['nickname'].id,
            'name': participant['nickname'].name,
            'rank': rank,
            'tie_value': seconds,
            'metrics': {
                'time': f'{seconds // 60}:{seconds % 60:02d}',
                'points': total_results - rank + 1,
            },
        })

    context = {
        'event': event,
        'participants': participants,
        'scoreboard': {
            'table_id': 'running-standings',
            'table_class': 'table-striped table-sm mb-0',
            'header_variant': 'light',
            'move_policy': 'ties',
            'accent': '#0ea5e9',
            'accent_dark': '#0284c7',
            'columns': [
                {'key': 'time', 'label': 'Tid'},
                {'key': 'points', 'label': 'Poeng', 'emphasize': True},
            ],
            'rows': scoreboard_rows,
        },
    }
    return render(request, 'core/running.html', context)


def football_tournament(request, pk):
    """
    Render a football page where the tournament is played 3 times.
    Each time one player can be marked "out". Manual ordering may be
    saved per-round (these are stored as sub-activity rankings) and a
    final standing can be saved (activity_id=2).
    """
    event = get_object_or_404(Event, pk=pk)
    nicknames = list(event.nicknames.order_by('id').all())

    # Load any existing manual rankings for this activity and per-round
    # We store per-round rankings using a composite activity id: activity_id*10 + round
    def load_ranking_for(round_num=None):
        if round_num is None:
            aid = 2
        else:
            aid = 2 * 10 + int(round_num)
        rankings = ActivityRanking.objects.filter(event=event, activity_id=aid).order_by('rank').select_related('nickname')
        return [r.nickname.id for r in rankings]

    round_rankings = {
        1: load_ranking_for(1),
        2: load_ranking_for(2),
        3: load_ranking_for(3),
    }

    final_ranking = load_ranking_for(None)
    round_scoreboards, final_scoreboard = _build_tournament_scoreboards(
        nicknames, '#ef4444', '#dc2626'
    )

    context = {
        'event': event,
        'participants': nicknames,
        'round_rankings': round_rankings,
        'final_ranking': final_ranking,
        'round_scoreboards': round_scoreboards,
        'final_scoreboard': final_scoreboard,
        'activity': {'id': 2, 'name': 'Football'},
    }
    return render(request, 'core/football.html', context)


def basketball_tournament(request, pk):
    """
    Basketball page — mirrors the football view but uses activity_id=3.
    Behavior and UI are identical to football (3 rounds, manual per-round ordering,
    compute final totals and tie-breaking UI).
    """
    event = get_object_or_404(Event, pk=pk)
    nicknames = list(event.nicknames.order_by('id').all())

    def load_ranking_for(round_num=None):
        if round_num is None:
            aid = 3
        else:
            aid = 3 * 10 + int(round_num)
        rankings = ActivityRanking.objects.filter(event=event, activity_id=aid).order_by('rank').select_related('nickname')
        return [r.nickname.id for r in rankings]

    round_rankings = {
        1: load_ranking_for(1),
        2: load_ranking_for(2),
        3: load_ranking_for(3),
    }

    final_ranking = load_ranking_for(None)
    round_scoreboards, final_scoreboard = _build_tournament_scoreboards(
        nicknames, '#f59e0b', '#d97706'
    )

    context = {
        'event': event,
        'participants': nicknames,
        'round_rankings': round_rankings,
        'final_ranking': final_ranking,
        'round_scoreboards': round_scoreboards,
        'final_scoreboard': final_scoreboard,
        'activity': {'id': 3, 'name': 'Basketball'},
    }
    return render(request, 'core/basketball.html', context)


def dice_tournament(request, pk):
    """
    Dice game: single final standing only. Rank 1 will be awarded special
    points (handled in update_total_scores). We persist the final ordering
    using activity_id=5.
    """
    event = get_object_or_404(Event, pk=pk)
    nicknames = list(event.nicknames.order_by('id').all())

    def load_ranking_for_final():
        rankings = ActivityRanking.objects.filter(event=event, activity_id=5).order_by('rank').select_related('nickname')
        return [r.nickname.id for r in rankings]

    final_ranking = load_ranking_for_final()

    context = {
        'event': event,
        'participants': nicknames,
        'final_ranking': final_ranking,
        'scoreboard': {
            'table_id': 'final-standing',
            'table_class': '',
            'header_variant': 'accent',
            'move_policy': 'free',
            'accent': '#ec4899',
            'accent_dark': '#db2777',
            'columns': [],
            'rows': [
                {
                    'id': nickname.id,
                    'name': nickname.name,
                    'rank': index,
                    'metrics': {},
                }
                for index, nickname in enumerate(nicknames, start=1)
            ],
        },
        'activity': {'id': 5, 'name': 'Dice Game'},
    }
    return render(request, 'core/dice.html', context)
