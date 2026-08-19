from django.contrib import admin
from .models import Event, Nickname, ActivityRanking, TennisMatch, RunningResult, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ('display_name', 'user', 'created_at')
	search_fields = ('display_name', 'user__email')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ('name', 'status', 'start_date', 'end_date', 'created_at')
	list_filter = ('status',)


@admin.register(Nickname)
class NicknameAdmin(admin.ModelAdmin):
	list_display = ('name', 'event', 'user', 'total_score', 'created_at')
	list_filter = ('event',)


@admin.register(ActivityRanking)
class ActivityRankingAdmin(admin.ModelAdmin):
	list_display = ('event', 'nickname', 'activity_id', 'rank', 'created_at')


@admin.register(TennisMatch)
class TennisMatchAdmin(admin.ModelAdmin):
	list_display = ('event', 'player1', 'player2', 'winner', 'created_at')


@admin.register(RunningResult)
class RunningResultAdmin(admin.ModelAdmin):
	list_display = ('event', 'nickname', 'time_seconds', 'group_id', 'recorded_at')
