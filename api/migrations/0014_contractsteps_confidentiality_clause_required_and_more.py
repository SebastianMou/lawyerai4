# Generated by Django 5.1.2 on 2024-12-14 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_contractsteps_notarization'),
    ]

    operations = [
        migrations.AddField(
            model_name='contractsteps',
            name='confidentiality_clause_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contractsteps',
            name='dispute_resolution_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contractsteps',
            name='penalties_for_breach_required',
            field=models.BooleanField(default=False),
        ),
    ]