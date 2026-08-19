
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import IntegrityError

from ..models import Event, ActivityRanking, Nickname
from ..forms import EventForm, NicknameForm
from .scoring import ACTIVITIES # Import ACTIVITIES from the sibling module
from ..forms import InviteForm
from ..models import Invitation
from django.contrib.auth.decorators import login_required
from django.db.models import Q

try:
    # optional import if django-allauth is installed
    from allauth.socialaccount.models import SocialAccount
except Exception:
    SocialAccount = None


@login_required
def claim_nickname(request, pk, nickname_id):
    """Allow a logged-in user to claim an unclaimed nickname for an event.

    Only allowed if the user was invited to the event (by email or via a
    facebook invitation) and the user does not already have a claimed
    nickname for the same event. When django-allauth is present we treat
    presence of a facebook SocialAccount as sufficient to match a
    facebook-based Invitation.
    """
    event = get_object_or_404(Event, pk=pk)
    nick = get_object_or_404(Nickname, id=nickname_id, event=event)

    # Ensure the user is invited to this event (by email or facebook profile)
    # Event owner is always allowed
    invited = False
    inv_qs = Invitation.objects.filter(event=event)
    if request.user == getattr(event, 'owner', None):
        invited = True
    # If there are no invitations for this event, allow claiming by any logged-in user
    if not invited and not inv_qs.exists():
        invited = True
    if request.user.email:
        invited = invited or inv_qs.filter(email__iexact=request.user.email).exists()
    if not invited and SocialAccount is not None:
        # If the user has an attached Facebook social account and there are
        # facebook invitations for this event, consider them invited.
        if SocialAccount.objects.filter(user=request.user, provider='facebook').exists():
            fb_inv = inv_qs.filter(Q(facebook_profile__isnull=False) & ~Q(facebook_profile=''))
            if fb_inv.exists():
                invited = True

    if not invited:
        messages.error(request, 'You are not invited to this event and cannot claim a participant.')
        return redirect('event_detail', pk=event.pk)

    # Enforce one claim per user per event
    existing_claim = Nickname.objects.filter(event=event, user=request.user).exclude(pk=nick.pk).first()
    if existing_claim:
        messages.error(request, 'You have already claimed a participant for this event.')
        return redirect('event_detail', pk=event.pk)

    if nick.user and nick.user != request.user:
        messages.error(request, 'This nickname is already claimed by another user.')
        return redirect('event_detail', pk=event.pk)

    nick.user = request.user
    nick.save(update_fields=['user'])
    messages.success(request, f"You are now linked to '{nick.name}' for event '{event.name}'.")
    return redirect('event_detail', pk=event.pk)


@login_required
def claim_user_page(request, pk):
    """Render a small claim portal under the main site where a logged-in user
    can view and claim nicknames for the event. This keeps the flow on a
    separate URL such as /event/<pk>/claimuser/ instead of the event detail page.
    """
    event = get_object_or_404(Event, pk=pk)
    nicknames = event.nicknames.all().order_by('name')

    if request.method == 'POST':
        # Support both claim and unclaim actions
        action = request.POST.get('action', 'claim')
        nickname_id = request.POST.get('nickname_id')
        if not nickname_id:
            messages.error(request, 'No participant selected.')
            return redirect('claim_user_page', pk=event.pk)
        nick = get_object_or_404(Nickname, id=nickname_id, event=event)

        if action == 'unclaim':
            # Allow unclaim by the participant owner, the event owner, or staff
            if not (nick.user == request.user or request.user.is_staff or request.user == getattr(event, 'owner', None)):
                messages.error(request, 'You cannot unclaim this participant.')
                return redirect('claim_user_page', pk=event.pk)
            nick.user = None
            nick.save(update_fields=['user'])
            messages.success(request, f"You unclaimed '{nick.name}' for event '{event.name}'.")
            return redirect('claim_user_page', pk=event.pk)

        # action == 'claim'
        # Ensure the user is invited (event owner always allowed). If there
        # are no invitations for the event, allow any authenticated user to
        # claim.
        invited = False
        inv_qs = Invitation.objects.filter(event=event)
        if request.user == getattr(event, 'owner', None):
            invited = True
        if not invited and not inv_qs.exists():
            invited = True
        if request.user.email:
            invited = invited or inv_qs.filter(email__iexact=request.user.email).exists()
        if not invited and SocialAccount is not None:
            if SocialAccount.objects.filter(user=request.user, provider='facebook').exists():
                fb_inv = inv_qs.filter(Q(facebook_profile__isnull=False) & ~Q(facebook_profile=''))
                if fb_inv.exists():
                    invited = True

        if not invited:
            messages.error(request, 'You are not invited to this event and cannot claim a participant.')
            return redirect('claim_user_page', pk=event.pk)

        # Enforce one claim per user per event
        existing_claim = Nickname.objects.filter(event=event, user=request.user).exclude(pk=nick.pk).first()
        if existing_claim:
            messages.error(request, 'You have already claimed a participant for this event.')
            return redirect('claim_user_page', pk=event.pk)

        if nick.user and nick.user != request.user:
            messages.error(request, 'This nickname is already claimed by another user.')
            return redirect('claim_user_page', pk=event.pk)

        nick.user = request.user
        nick.save(update_fields=['user'])
        messages.success(request, f"You claimed '{nick.name}' for event '{event.name}'.")
        return redirect('claim_user_page', pk=event.pk)

    context = {
        'event': event,
        'nicknames': nicknames,
    }
    return render(request, 'core/claim_user.html', context)

def event_list(request):
    """Show only featured events and those relevant to the logged-in user."""
    if request.user.is_authenticated:
        user_event_ids = set(Event.objects.filter(owner=request.user).values_list('pk', flat=True))

        user_email_invites = Invitation.objects.filter(
            email__iexact=request.user.email,
        ).values_list('event_id', flat=True)
        user_event_ids.update(user_email_invites)

        if SocialAccount is not None:
            facebook_account = SocialAccount.objects.filter(user=request.user, provider='facebook').exists()
            if facebook_account:
                facebook_event_ids = Invitation.objects.filter(
                    facebook_profile__isnull=False,
                ).exclude(facebook_profile='').values_list('event_id', flat=True)
                user_event_ids.update(facebook_event_ids)
    else:
        user_event_ids = set()

    all_events = Event.objects.filter(
        Q(status='featured')
        | Q(pk__in=user_event_ids)
    ).distinct()

    featured_events = [e for e in all_events if e.get_dynamic_status() == 'featured']
    ongoing_events = [e for e in all_events if e.get_dynamic_status() == 'ongoing' and e.pk in user_event_ids]
    past_events = [e for e in all_events if e.get_dynamic_status() == 'past' and e.pk in user_event_ids]
    future_events = [e for e in all_events if e.get_dynamic_status() == 'future' and e.pk in user_event_ids]

    context = {
        'featured_events': featured_events,
        'ongoing_events': ongoing_events,
        'past_events': past_events,
        'future_events': future_events,
    }
    return render(request, 'core/event_list.html', context)

def event_detail(request, pk):
    """Displays details for a single event, its nicknames, and allows adding nicknames."""
    event = get_object_or_404(Event, pk=pk)
    nicknames = event.nicknames.all()

    invite_form = InviteForm()
    form = NicknameForm(event=event)
    if request.method == 'POST':
        # Distinguish between nickname posts and invite posts
        if 'invite_submit' in request.POST:
            invite_form = InviteForm(request.POST)
            if invite_form.is_valid():
                if not request.user.is_authenticated:
                    messages.error(request, 'You must be logged in to invite people. Please log in and try again.')
                    return redirect('account_login')
                inv = Invitation(
                    inviter=request.user,
                    event=event,
                    email=invite_form.cleaned_data.get('email', ''),
                    invitee_display_name=invite_form.cleaned_data.get('display_name', ''),
                )
                inv.save()
                messages.success(request, 'Invitation saved for this event.')
                return redirect('event_detail', pk=event.pk)
            else:
                messages.error(request, 'Could not create invitation. Please correct errors below.')
        else:
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

    # Build a per-nickname breakdown of points per activity so the template
    # can show where each participant got their points. Points calculation
    # mirrors update_total_scores: points = total_participants - rank + 1
    total_participants = nicknames.count()
    breakdown = {}
    for nickname in nicknames:
        per_activity = {}
        for activity in ACTIVITIES:
            rankings_qs = activity_rankings.get(activity['id'])
            # Try to find this nickname in the rankings for the activity
            rank_obj = rankings_qs.filter(nickname=nickname).first() if rankings_qs is not None else None
            if rank_obj:
                points = total_participants - rank_obj.rank + 1
            else:
                points = 0
            per_activity[activity['id']] = points
        breakdown[nickname.id] = per_activity

    # Check if all games are scored (all activities have rankings for all participants)
    all_games_scored = False
    if total_participants > 0:
        all_games_scored = True
        for activity in ACTIVITIES:
            rankings_qs = activity_rankings.get(activity['id'], [])
            if len(list(rankings_qs)) != total_participants:
                all_games_scored = False
                break

    context = {
        'event': event,
        'nicknames': nicknames,
        'nickname_form': form,
        'invite_form': invite_form,
        'event_url': request.build_absolute_uri(event.get_absolute_url()),
        'activities': ACTIVITIES,
        'total_participants': nicknames.count(),
        'activity_rankings': activity_rankings,
        'breakdown': breakdown,
        'all_games_scored': all_games_scored,
    }
    return render(request, 'core/event_detail.html', context)

def event_create(request):
    """Handles creation of a new event."""
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.status = event.status or 'future'
            # If a logged-in user creates the event, set them as owner
            if request.user.is_authenticated:
                event.owner = request.user
            event.save()
            messages.success(request, f"Event '{event.name}' created successfully!")
            return redirect(event.get_absolute_url())
        else:
             messages.error(request, "Please correct the errors below.")
    else:
        form = EventForm()

    context = {'form': form}
    return render(request, 'core/event_create.html', context)


@login_required
def portal(request):
    """Simple user portal showing invitations the user has received and claimed events."""
    display_name = getattr(getattr(request.user, 'profile', None), 'display_name', '')
    invitation_filter = Q(email__iexact=request.user.email)
    if display_name:
        invitation_filter |= Q(invitee_display_name__iexact=display_name)
    invitations = Invitation.objects.filter(invitation_filter).exclude(inviter=request.user)
    claimed_nicknames = Nickname.objects.filter(user=request.user).select_related('event')
    context = {'invitations': invitations, 'claimed_nicknames': claimed_nicknames}
    return render(request, 'core/portal.html', context)