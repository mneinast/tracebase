# Generated by Django 3.2.5 on 2022-08-09 15:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DataRepo', '0002_alter_tracer_compound'),
    ]

    operations = [
        migrations.CreateModel(
            name='PeakGroupLabel',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('element', models.CharField(choices=[('C', 'Carbon'), ('N', 'Nitrogen'), ('H', 'Hydrogen'), ('O', 'Oxygen'), ('S', 'Sulfur'), ('P', 'Phosphorus')], default='C', help_text='The type of element that is labeled in this observation (e.g. "C", "H", "O").', max_length=1)),
                ('peak_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='peak_group_labels', to='DataRepo.peakgroup')),
            ],
            options={
                'verbose_name': 'labeled element',
                'verbose_name_plural': 'labeled elements',
                'ordering': ['peak_group', 'element'],
            },
        ),
        migrations.CreateModel(
            name='AnimalLabel',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('element', models.CharField(choices=[('C', 'Carbon'), ('N', 'Nitrogen'), ('H', 'Hydrogen'), ('O', 'Oxygen'), ('S', 'Sulfur'), ('P', 'Phosphorus')], default='C', help_text='An element that is labeled in any of the tracers in this infusate (e.g. "C", "H", "O").', max_length=1)),
                ('animal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='animal_labels', to='DataRepo.animal')),
            ],
            options={
                'verbose_name': 'animal_label',
                'verbose_name_plural': 'animal_labels',
                'ordering': ['animal', 'element'],
            },
        ),
        migrations.AddConstraint(
            model_name='peakgrouplabel',
            constraint=models.UniqueConstraint(fields=('peak_group', 'element'), name='unique_peakgrouplabel'),
        ),
        migrations.AddConstraint(
            model_name='animallabel',
            constraint=models.UniqueConstraint(fields=('animal', 'element'), name='unique_animal_label'),
        ),
    ]