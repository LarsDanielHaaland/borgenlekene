
from django.db import models
from django.urls import reverse

class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
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

class Nickname(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='nicknames')
    name = models.CharField(max_length=100)
    total_score = models.IntegerField(default=0)
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
                    self.pk = existing.pk
        except Exception:
            # Be permissive — on error we'll let the normal save raise the
            # appropriate exception (e.g., integrity error) so it isn't masked.
            pass

        super().save(*args, **kwargs)


class Invitation(models.Model):
    """Store invitations created by users for events or external persons."""
    inviter = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(blank=True)
    facebook_profile = models.URLField(blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.email or self.facebook_profile or 'unknown'
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