# Generated by Django 3.2.4 on 2021-06-16 22:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("DataRepo", "0002_RemoveDefaultProtocolCategory"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="animal",
            name="state",
        ),
        migrations.AlterField(
            model_name="animal",
            name="feeding_status",
            field=models.CharField(
                blank=True,
                help_text='The laboratory coded dietary state for the animal, also referred to as "Animal State" (e.g. "fasted").',
                max_length=256,
                null=True,
            ),
        ),
    ]
