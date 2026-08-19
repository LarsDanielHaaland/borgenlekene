
from django.db import models
from django.urls import reverse
from django.conf import settings

class Event(models.Model):
    STATUS_CHOICES = [
        ('featured', 'Featured'),
        ('ongoing', 'Ongoing'),
        ('past', 'Past'),
        ('future', 'Future'),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='future')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    # Optional owner of the event (the user who created it)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'pk': self.pk})

    def get_nickname_count(self):
        return self.nicknames.count()

    def get_dynamic_status(self):
        """Return the status based on dates, unless manually set to featured."""
        from django.utils import timezone
        now = timezone.now()
        if self.status == 'featured':
            return 'featured'
        if self.start_date and self.end_date:
            if now < self.start_date:
                return 'future'
            elif self.start_date <= now <= self.end_date:
                return 'ongoing'
            else:
                return 'past'
        return self.status  # fallback to manual status if dates not set

class Profile(models.Model):
    """Extra per-user data: a globally unique display name shown across the site."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class Nickname(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='nicknames')
    name = models.CharField(max_length=100)
    total_score = models.IntegerField(default=0)
    # Optional link to the Django user who 'owns' or claimed this nickname
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='nicknames')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'name')
        ordering = ['-total_score', 'name']  # Order by score desc, then name

    def __str__(self):
        return f"{self.name} ({self.event.name})"

class ActivityRanking(models.Model):
    """Store rankings for each activity for each participant."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nickname = models.ForeignKey(Nickname, on_delete=models.CASCADE)
    activity_id = models.IntegerField()  # 1=Tennis, 2=Football, etc.
    rank = models.IntegerField()  # 1=first place, 2=second place, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'nickname', 'activity_id')
        ordering = ['activity_id', 'rank']

    def __str__(self):
        return f"{self.nickname.name} - Activity {self.activity_id} - Rank {self.rank}"

class TennisMatch(models.Model):
    """Store tennis match results."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player1 = models.ForeignKey(Nickname, on_delete=models.CASCADE, related_name='tennis_matches_as_player1')
    player2 = models.ForeignKey(Nickname, on_delete=models.CASCADE, related_name='tennis_matches_as_player2')
    winner = models.ForeignKey(Nickname, on_delete=models.CASCADE, related_name='tennis_wins')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'player1', 'player2')

    def __str__(self):
        return f"{self.player1.name} vs {self.player2.name} (Winner: {self.winner.name})"

    def get_loser(self):
        return self.player2 if self.winner == self.player1 else self.player1
    
    def save(self, *args, **kwargs):
        """Ensure a canonical ordering for player1/player2 to avoid duplicate swapped matches."""
        # Canonicalize by player id order so (a,b) and (b,a) map to the same
        # stored match. When an existing canonical match exists, update it
        # instead of creating a new row to respect the unique constraint.
        try:
            if self.player1_id and self.player2_id and self.player1_id > self.player2_id:
                self.player1, self.player2 = self.player2, self.player1

            # If this is a new instance (no pk yet), check for an existing
            # canonical match and if found, update that row instead of
            # inserting a duplicate.
            if not self.pk:
                existing = TennisMatch.objects.filter(
                    event=self.event,
                    player1_id=self.player1_id,
                    player2_id=self.player2_id,
                ).first()
                if existing:
                    # Update the pk so save() will perform an update
                    # Preserve the existing PK and ensure any automatically
                    # populated fields (like created_at) are preserved on
                    # the instance so that a subsequent UPDATE does not
                    # overwrite them with NULL.
                    self.pk = existing.pk
                    try:
                        # copy created_at if present on the existing row
                        self.created_at = existing.created_at
                    except Exception:
                        pass
        except Exception:
            # Be permissive — on error we'll let the normal save raise the
            # appropriate exception (e.g., integrity error) so it isn't masked.
            pass

        # If callers explicitly requested a force_insert (QuerySet.create
        # does this), but we've discovered an existing PK to update, convert
        # the operation into an update to avoid attempting an insert with a
        # duplicate primary key which causes an IntegrityError on SQLite.
        if kwargs.get('force_insert') and self.pk:
            kwargs.pop('force_insert')
            kwargs['force_update'] = True

        super().save(*args, **kwargs)


class Invitation(models.Model):
    """Store invitations created by users for events or external persons."""
    inviter = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(blank=True)
    invitee_display_name = models.CharField(max_length=50, blank=True)
    facebook_profile = models.URLField(blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.email or self.invitee_display_name or 'unknown'
        return f"Invitation by {self.inviter} to {target}"


class RunningResult(models.Model):
    """Store running times per participant for an event.

    time_seconds: float time in seconds
    group_id: optional int to associate group starts
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nickname = models.ForeignKey(Nickname, on_delete=models.CASCADE)
    time_seconds = models.FloatField()
    group_id = models.IntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'nickname')
        ordering = ['time_seconds']

    def __str__(self):
        return f"{self.nickname.name} - {self.time_seconds}s"