
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import IntegrityError

from ..models import Event, ActivityRanking
from ..forms import EventForm, NicknameForm
from .scoring import ACTIVITIES # Import ACTIVITIES from the sibling module
from ..forms import InviteForm
from ..models import Invitation
from django.contrib.auth.decorators import login_required

def event_list(request):
    """Displays a list of all events."""
    events = Event.objects.all().order_by('-created_at')
    context = {'events': events}
    return render(request, 'core/event_list.html', context)

def event_detail(request, pk):
    """Displays details for a single event, its nicknames, and allows adding nicknames."""
    event = get_object_or_404(Event, pk=pk)
    nicknames = event.nicknames.all()

    invite_form = InviteForm()
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
                    facebook_profile=invite_form.cleaned_data.get('facebook_profile', ''),
                    message=invite_form.cleaned_data.get('message', ''),
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

    context = {
        'event': event,
        'nicknames': nicknames,
        'nickname_form': form,
        'invite_form': invite_form,
        'event_url': request.build_absolute_uri(event.get_absolute_url()),
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
            event = form.save()
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
    """Simple user portal where the logged-in user can invite people to events."""
    if request.method == 'POST':
        form = InviteForm(request.POST)
        if form.is_valid():
            inv = Invitation(
                inviter=request.user,
                event=form.cleaned_data.get('event'),
                email=form.cleaned_data.get('email', ''),
                facebook_profile=form.cleaned_data.get('facebook_profile', ''),
                message=form.cleaned_data.get('message', ''),
            )
            inv.save()
            # Note: actual sending (email/Facebook API) not implemented here
            messages.success(request, 'Invitation saved. You can send it via email or Facebook externally.')
            return redirect('portal')
        else:
            messages.error(request, 'Could not create invitation. Please correct errors below.')
    else:
        form = InviteForm()

    invitations = Invitation.objects.filter(inviter=request.user)
    context = {'form': form, 'invitations': invitations}
    return render(request, 'core/portal.html', context)