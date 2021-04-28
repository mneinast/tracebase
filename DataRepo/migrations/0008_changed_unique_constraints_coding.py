# Generated by Django 3.1.8 on 2021-04-28 22:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DataRepo', '0007_peakdata_validator'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='peakdata',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='peakgroup',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='msrun',
            constraint=models.UniqueConstraint(
                fields=('researcher', 'date', 'protocol', 'sample'),
                name='unique_msrun'),
        ),
        migrations.AddConstraint(
            model_name='peakdata',
            constraint=models.UniqueConstraint(
                fields=('peak_group', 'labeled_element', 'labeled_count'),
                name='unique_peakdata'),
        ),
        migrations.AddConstraint(
            model_name='peakgroup',
            constraint=models.UniqueConstraint(
                fields=('name', 'ms_run'),
                name='unique_peakgroup'),
        ),
    ]
