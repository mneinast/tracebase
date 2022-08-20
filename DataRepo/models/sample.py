import warnings
from datetime import date, timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from DataRepo.models.hier_cached_model import HierCachedModel, cached_function

from .peak_data import PeakData
from .peak_group import PeakGroup


class Sample(HierCachedModel):
    parent_related_key_name = "animal"
    child_related_key_names = ["msruns", "fcircs"]

    # Instance / model fields
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=256,
        unique=True,
        help_text="The unique name of the biological sample.",
    )
    date = models.DateField(
        default=date.today, help_text="The date the sample was collected."
    )
    researcher = models.CharField(
        max_length=256,
        help_text='The name of the researcher who prepared the sample (e.g. "Alex Medina").',
    )
    animal = models.ForeignKey(
        to="DataRepo.Animal",
        on_delete=models.CASCADE,
        null=False,
        related_name="samples",
        help_text="The source animal from which the sample was extracted.",
    )
    tissue = models.ForeignKey(
        to="DataRepo.Tissue",
        on_delete=models.RESTRICT,
        null=False,
        related_name="samples",
        help_text="The tissue type this sample was taken from.",
    )

    """
    researchers have advised that samples might have a time_collected up to a
    day prior-to and a week after infusion
    """
    MINIMUM_VALID_TIME_COLLECTED = timedelta(days=-1)
    MAXIMUM_VALID_TIME_COLLECTED = timedelta(weeks=1)
    time_collected = models.DurationField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MINIMUM_VALID_TIME_COLLECTED),
            MaxValueValidator(MAXIMUM_VALID_TIME_COLLECTED),
        ],
        help_text="The time, relative to an infusion timepoint, "
        "that a sample was extracted from an animal.",
    )

    @property  # type: ignore
    @cached_function
    def is_serum_sample(self):
        """returns True if the sample is flagged as a "serum" sample"""
        return self.tissue.is_serum()

    def peak_groups(self, compound=None):
        """
        Retrieve a list of PeakGroup objects for a sample.  If an optional compound is passed (e.g.
        animal.infusate.tracers.compound), then is it used to filter the PeakGroup queryset to a specific compound's
        peakgroups.
        """
        from DataRepo.models.compound import Compound
        from DataRepo.models.tracer import Tracer

        peak_groups = PeakGroup.objects.filter(msrun__sample_id=self.id)
        if compound:
            if isinstance(compound, Compound):
                peak_groups = peak_groups.filter(compounds__id=compound.id)
            elif isinstance(compound, Tracer):
                peak_groups = peak_groups.filter(compounds__id=compound.compound.id)
            else:
                raise InvalidArgument("Argument must be a Compound or Tracer")
        return peak_groups.all()

    def last_peak_group(self, compound):
        """
        Retrieve the latest PeakGroup of this sample for a given compound.
        """

        # NOTE: PR REVIEW (TO BE DELETED): I have noted that it should be possible to calculate all the below values
        # based on the "not last" peak group of a serum sample.  For example, if Lysine was the tracer, and it was
        # included in an msrun twice for the same serum sample, calculating based on it might be worthwhile for the
        # same reason that we show calculations for the "not last" serum sample.  If people think that's worthwhile, I
        # could hang this table off of peakGroup instead of here...
        peakgroups = self.peak_groups(compound.id)
        peakgroups = peakgroups.order_by("msrun__date")

        if peakgroups.count() == 0:
            warnings.warn(
                f"Serum sample {self.name} has no peak group for compound {compound}."
            )
            return None

        return peakgroups.last()

    def peak_data(self, compound=None):
        """
        Retrieve a list of PeakData objects for a sample.  If an optional compound is passed (e.g.
        animal.infusate.tracers.compound), then is it used to filter the PeakData queryset to a specific compound's
        peakgroups.
        """
        from DataRepo.models.compound import Compound
        from DataRepo.models.tracer import Tracer

        peakdata = PeakData.objects.filter(peak_group__msrun__sample_id=self.id)

        if compound:
            if isinstance(compound, Compound):
                peakdata = peakdata.filter(peak_group__compounds__id=compound.id)
            elif isinstance(compound, Tracer):
                peakdata = peakdata.filter(
                    peak_group__compounds__id=compound.compound.id
                )
            else:
                raise InvalidArgument("Argument must be a Compound or Tracer")

        return peakdata.all()

    class Meta:
        verbose_name = "sample"
        verbose_name_plural = "samples"
        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class InvalidArgument(ValueError):
    pass
