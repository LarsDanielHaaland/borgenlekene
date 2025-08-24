
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