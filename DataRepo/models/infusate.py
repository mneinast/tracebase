from django.core.exceptions import ValidationError
from django.db import models

from DataRepo.models.maintained_model import (
    MaintainedModel,
    field_updater_function,
)
from DataRepo.models.tracer import Tracer

CONCENTRATION_SIGNIFICANT_FIGURES = 3


class Infusate(MaintainedModel):

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=256,
        unique=True,
        null=True,
        editable=False,
        help_text="A unique name or lab identifier of the infusate 'recipe' containing 1 or more tracer compounds at "
        "specific concentrations.",
    )
    tracer_group_name = models.CharField(
        max_length=20,
        unique=False,
        null=True,
        blank=True,
        help_text="A short name or lab identifier of refering to a group of tracer compounds, e.g '6eaas'.  There may "
        "be multiple infusate records with this group name, each referring to the same tracers at different "
        "concentrations.",
    )
    tracers = models.ManyToManyField(
        Tracer,
        through="InfusateTracer",
        help_text="Tracers included in this infusate 'recipe' at specific concentrations.",
        related_name="infusates",
    )

    class Meta:
        verbose_name = "infusate"
        verbose_name_plural = "infusates"
        ordering = ["name"]

    def __str__(self):
        return str(self._name())

    @field_updater_function(generation=0, update_field_name="name", update_label="name")
    def _name(self):
        # Format: `tracer_group_name{tracername;tracername}`

        # Need to check self.id to see if the record exists yet or not, because if it does not yet exist, we cannot use
        # the reverse self.tracers reference until it exists (besides, another update will trigger when the
        # InfusateTracer records are created).  Otherwise, the following exception is thrown:
        # ValueError: "<Infusate: >" needs to have a value for field "id" before this many-to-many relationship can be
        # used.
        if self.id is None or self.tracers is None or self.tracers.count() == 0:
            return self.tracer_group_name

        link_recs = self.tracers.through.objects.filter(infusate__exact=self.id)

        name = ";".join(
            sorted(
                map(
                    lambda o: o.tracer._name()
                    + f"[{o.concentration:.{CONCENTRATION_SIGNIFICANT_FIGURES}g}]",
                    link_recs.all(),
                )
            )
        )

        if self.tracer_group_name is not None:
            name = f"{self.tracer_group_name} {{{name}}}"

        return name

    def clean(self, *args, **kwargs):
        """
        This is an override of clean to validate the tracer_group_name of new records
        """
        self.validate_tracer_group_names(name=self.tracer_group_name)
        super().clean(*args, **kwargs)

    @classmethod
    def validate_tracer_group_names(cls, name=None):
        """
        Validation method that raises and exception if two infusate records share a tracer_group_name but are not
        composed of the same group of tracers.  If you want to check an object instance's name only, you must supply
        the name as an argument.
        """
        if name is None:
            grouped_recs = cls.objects.filter(tracer_group_name__isnull=False)
        else:
            grouped_recs = cls.objects.filter(tracer_group_name__iexact=name)

        cls.validate_tracer_group_names_helper(grouped_recs)

    @classmethod
    def validate_tracer_group_names_helper(cls, grouped_recs):
        # Build a 2-level dict whose keys are the tracer_group_name and a "tracer key".  The "tracer key" is the sorted
        # IDs of tracer records concatenated together with a delimiting comma.  The value is a list of Infusate record
        # IDs.
        group_map_dict = {}
        for group_rec in grouped_recs:
            grp_name = group_rec.tracer_group_name
            if grp_name not in group_map_dict:
                group_map_dict[grp_name] = {}
            tracer_key = ",".join(
                sorted(map(lambda r: str(r.id), group_rec.tracers.all()))
            )
            if tracer_key not in group_map_dict[grp_name]:
                group_map_dict[grp_name][tracer_key] = []
            group_map_dict[grp_name][tracer_key].append(group_rec.id)

        # For each tracer_group name, if it refers to multiple groups of tracers, append an error message to the
        # problems array that identifies the ambiguous tracer_group_names, the number of different groupings of
        # tracers, a description of the different sets of tracers, and a single example list of the infusate record IDs
        # with the problematic tracer_group_names.
        problems = []
        for grp_name in group_map_dict:
            if len(group_map_dict[grp_name].keys()) != 1:
                num_groupings = len(group_map_dict[grp_name].keys())
                stats = "\n"
                i = 0
                for tracer_key in sorted(
                    group_map_dict[grp_name],
                    key=lambda x: len(group_map_dict[grp_name][x]),
                    reverse=True,
                ):
                    stats += (
                        f"Tracer IDs: {tracer_key} are refered to by {len(group_map_dict[grp_name][tracer_key])} "
                        "infusate records"
                    )
                    i += 1
                    if i == num_groupings:
                        stats += (
                            f", this last one with the following IDs: "
                            f"{','.join(group_map_dict[grp_name][tracer_key])}"
                        )
                    else:
                        stats += "\n"
                msg = (
                    f"Tracer group name {grp_name} is inconsistent.  There are {num_groupings} different groupings of "
                    "different tracer records.  This group name refers to the following list of tracer IDs by the "
                    f"indicated number of infusate records: {stats}"
                )
                problems.append(msg)
        if len(problems) > 0:
            raise ValidationError("\n".join(problems))