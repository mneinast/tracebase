from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.functional import cached_property

from .peak_group import PeakGroup
from .tracer_labeled_class import TracerLabeledClass


class PeakData(models.Model, TracerLabeledClass):
    """
    PeakData is a single observation (at the most atomic level) of a MS-detected molecule.
    For example, this could describe the data for M+2 in glucose from mouse 345 brain tissue.
    """

    id = models.AutoField(primary_key=True)
    peak_group = models.ForeignKey(
        to="DataRepo.PeakGroup",
        on_delete=models.CASCADE,
        null=False,
        related_name="peak_data",
    )
    labeled_element = models.CharField(
        max_length=1,
        null=True,
        choices=TracerLabeledClass.TRACER_LABELED_ELEMENT_CHOICES,
        default=TracerLabeledClass.CARBON,
        blank=True,
        help_text='The type of element that is labeled in this observation (e.g. "C", "H", "O").',
    )
    labeled_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(TracerLabeledClass.MAX_LABELED_ATOMS),
        ],
        help_text="The number of labeled atoms (M+) observed relative to the "
        "presumed compound referred to in the peak group.",
    )
    raw_abundance = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="The ion count of this observation.",
    )
    corrected_abundance = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="The ion counts corrected for natural abundance of isotopomers.",
    )
    med_mz = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="The median mass/charge value of this measurement.",
    )
    med_rt = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="The median retention time value of this measurement.",
    )

    # @cached_function is *slower* than uncached
    @cached_property
    def fraction(self):
        """
        The corrected abundance of the labeled element in this PeakData as a
        fraction of the total abundance of the labeled element in this
        PeakGroup.

        Accucor calculates this as "Normalized", but TraceBase renames it to
        "fraction" to avoid confusion with other variables like "normalized
        labeling".
        """
        try:
            fraction = self.corrected_abundance / self.peak_group.total_abundance
        except ZeroDivisionError:
            fraction = None
        return fraction

    class Meta:
        verbose_name = "peak data"
        verbose_name_plural = "peak data"
        ordering = ["peak_group", "labeled_count"]

        # composite key
        constraints = [
            models.UniqueConstraint(
                fields=["peak_group", "labeled_element", "labeled_count"],
                name="unique_peakdata",
            )
        ]
