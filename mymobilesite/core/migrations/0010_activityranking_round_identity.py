from django.db import migrations, models


def decode_legacy_rounds(apps, schema_editor):
    ActivityRanking = apps.get_model("core", "ActivityRanking")
    for ranking in ActivityRanking.objects.all().iterator():
        if ranking.activity_id < 10:
            continue

        activity_id, round_number = divmod(ranking.activity_id, 10)
        if activity_id in {1, 2, 3, 4, 5} and 1 <= round_number <= 3:
            ranking.activity_id = activity_id
            ranking.round_number = round_number
            ranking.save(update_fields=["activity_id", "round_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_invitation_invitee_display_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="activityranking",
            name="round_number",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.RunPython(
            decode_legacy_rounds,
            migrations.RunPython.noop,
        ),
        migrations.AlterUniqueTogether(
            name="activityranking",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="activityranking",
            constraint=models.UniqueConstraint(
                condition=models.Q(round_number__isnull=False),
                fields=("event", "nickname", "activity_id", "round_number"),
                name="unique_activity_ranking_round",
            ),
        ),
        migrations.AddConstraint(
            model_name="activityranking",
            constraint=models.UniqueConstraint(
                condition=models.Q(round_number__isnull=True),
                fields=("event", "nickname", "activity_id"),
                name="unique_activity_ranking_final",
            ),
        ),
        migrations.AlterModelOptions(
            name="activityranking",
            options={"ordering": ["activity_id", "round_number", "rank"]},
        ),
    ]
