from DataRepo.models.maintained_model import (
    MaintainedModel,
    field_updater_function,
)
from DataRepo.models.tracer import Tracer
from django.db import models


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
    short_name = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="A unique short name or lab identifier of the infusate 'recipe' containing 1 or more tracer "
        "compounds at specific concentrations, e.g '6eaas'.",
    )
    tracers = models.ManyToManyField(
        Tracer,
        through="InfusateTracer",
        help_text="Tracers included in this infusate 'recipe'.",
        related_name="infusates",
    )

    class Meta:
        verbose_name = "infusate"
        verbose_name_plural = "infusates"
        ordering = ["name"]

    def __str__(self):
        return str(self._name())

    @field_updater_function(generation=0, update_field_name="name")
    def _name(self):
        # Format: `short_name{tracername;tracername}`

        # Need to check self.id to see if the record exists yet or not, because if it does not yet exist, we cannot use
        # the reverse self.tracers reference until it exists (besides, another update will trigger when the
        # InfusateTracer records are created).  Otherwise, the following exception is thrown:
        # ValueError: "<Infusate: >" needs to have a value for field "id" before this many-to-many relationship can be
        # used.
        if self.id is None or self.tracers is None or self.tracers.count() == 0:
            return self.short_name
        return (
            self.short_name
            + "{"
            + ";".join(sorted(map(lambda o: o._name(), self.tracers.all())))
            + "}"
        )
