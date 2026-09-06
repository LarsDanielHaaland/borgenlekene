from datetime import datetime, time as dt_time

from django import forms
from django.utils import timezone
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from .models import Event, Nickname, Profile

DEFAULT_EVENT_TIME = dt_time(10, 0)


class DisplayNameMixin(forms.Form):
    """Adds a globally-unique display name field to a signup form."""
    display_name = forms.CharField(
        max_length=50,
        label='Visningsnavn',
        widget=forms.TextInput(attrs={'placeholder': 'Velg et unikt visningsnavn'}),
    )

    def clean_display_name(self):
        name = self.cleaned_data.get('display_name', '').strip()
        if not name:
            raise forms.ValidationError("Visningsnavn kan ikke være tomt.")
        if Profile.objects.filter(display_name__iexact=name).exists():
            raise forms.ValidationError(f"Visningsnavnet '{name}' er allerede tatt.")
        return name

    def save(self, request):
        user = super().save(request)
        Profile.objects.create(user=user, display_name=self.cleaned_data['display_name'])
        return user


class CustomSignupForm(DisplayNameMixin, SignupForm):
    """Regular email/password signup form with a required unique display name."""
    pass


class CustomSocialSignupForm(DisplayNameMixin, SocialSignupForm):
    """Social (e.g. Facebook) signup form asking for a unique display name."""
    pass


class EventForm(forms.ModelForm):
    """Form for creating/editing an Event."""
    status = forms.ChoiceField(
        choices=Event.STATUS_CHOICES,
        required=False,
        initial='future',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    event_date = forms.DateField(
        required=False,
        label='Dato',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    event_time = forms.TimeField(
        required=False,
        label='Starttid',
        initial=DEFAULT_EVENT_TIME,
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )

    class Meta:
        model = Event
        fields = ['name', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].required = False
        if not self.data.get('status') and not self.initial.get('status'):
            self.fields['status'].initial = 'future'
        if self.instance and self.instance.pk and self.instance.start_date:
            local_start = timezone.localtime(self.instance.start_date)
            self.fields['event_date'].initial = local_start.date()
            self.fields['event_time'].initial = local_start.time()

    def clean_status(self):
        return self.cleaned_data.get('status') or 'future'

    def save(self, commit=True):
        event = super().save(commit=False)
        event_date = self.cleaned_data.get('event_date')
        event_time = self.cleaned_data.get('event_time') or DEFAULT_EVENT_TIME
        if event_date:
            naive_start = datetime.combine(event_date, event_time)
            naive_end = datetime.combine(event_date, dt_time(23, 59, 59))
            event.start_date = timezone.make_aware(naive_start) if timezone.is_naive(naive_start) else naive_start
            event.end_date = timezone.make_aware(naive_end) if timezone.is_naive(naive_end) else naive_end
        else:
            event.start_date = None
            event.end_date = None
        if commit:
            event.save()
        return event

class NicknameForm(forms.ModelForm):
    """Form for adding a Nickname to an Event."""
    class Meta:
        model = Nickname
        fields = ['name'] # Only need the name field from the user

    def __init__(self, *args, **kwargs):
        # We need the event to check for uniqueness within that specific event
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'placeholder': 'Enter new nickname'})

    def clean_name(self):
        """Ensure the nickname is unique for the associated event."""
        name = self.cleaned_data.get('name').strip()
        if not name:
            raise forms.ValidationError("Nickname cannot be empty.")
        if self.event and Nickname.objects.filter(event=self.event, name=name).exists():
            raise forms.ValidationError(f"The nickname '{name}' already exists in this event.")
        return name


class InviteForm(forms.Form):
    """Invite form to invite by email or by unique display name."""
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=False)
    email = forms.EmailField(required=False)
    display_name = forms.CharField(required=False, label='Visningsnavn')

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        display_name = cleaned.get('display_name', '').strip()
        cleaned['display_name'] = display_name
        if not email and not display_name:
            raise forms.ValidationError('Angi enten en e-post eller et visningsnavn for å invitere.')
        if display_name and not Profile.objects.filter(display_name__iexact=display_name).exists():
            raise forms.ValidationError(f"Fant ingen bruker med visningsnavnet '{display_name}'.")
        return cleaned