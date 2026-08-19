from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_event_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='status',
            field=models.CharField(choices=[('featured', 'Featured'), ('ongoing', 'Ongoing'), ('past', 'Past'), ('future', 'Future')], default='future', max_length=20),
        ),
    ]