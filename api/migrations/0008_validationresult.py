# Generated by Django 5.1.2 on 2024-12-05 19:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_alter_contractsteps_termination_clause'),
    ]

    operations = [
        migrations.CreateModel(
            name='ValidationResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('check_type', models.CharField(max_length=255)),
                ('passed', models.BooleanField()),
                ('issues', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='validation_results', to='api.contractsteps')),
            ],
        ),
    ]
