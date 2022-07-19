# Generated by Django 3.2.5 on 2022-07-12 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DataRepo', '0002_tracer_group_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='peakdatalabel',
            name='element',
            field=models.CharField(choices=[('C', 'Carbon'), ('N', 'Nitrogen'), ('H', 'Hydrogen'), ('O', 'Oxygen'), ('S', 'Sulfur'), ('P', 'Phosphorus')], default='C', help_text='The type of element that is labeled in this observation (e.g. "C", "H", "O").', max_length=1),
        ),
        migrations.AlterField(
            model_name='tracerlabel',
            name='element',
            field=models.CharField(choices=[('C', 'Carbon'), ('N', 'Nitrogen'), ('H', 'Hydrogen'), ('O', 'Oxygen'), ('S', 'Sulfur'), ('P', 'Phosphorus')], default='C', help_text='The type of atom that is labeled in the tracer compound (e.g. "C", "H", "O").', max_length=1),
        ),
    ]