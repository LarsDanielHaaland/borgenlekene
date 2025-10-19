from django import forms
from .models import Event, Nickname

class EventForm(forms.ModelForm):
    """Form for creating/editing an Event."""
    class Meta:
        model = Event
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

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
    """Simple invite form to invite by email or facebook profile URL."""
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=False)
    email = forms.EmailField(required=False)
    facebook_profile = forms.URLField(required=False)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows':3}), required=False)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        fb = cleaned.get('facebook_profile')
        if not email and not fb:
            raise forms.ValidationError('Provide either an email or a Facebook profile URL to invite.')
        return cleaned