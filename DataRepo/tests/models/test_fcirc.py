from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings, tag

from DataRepo.models import (
    Animal,
    FCirc,
    MSRun,
    PeakGroup,
    PeakGroupLabel,
    PeakGroupSet,
    Protocol,
    Sample,
)
from DataRepo.tests.tracebase_test_case import TracebaseTestCase


@override_settings(CACHES=settings.TEST_CACHES)
@tag("multi_working")
class FCircTests(TracebaseTestCase):
    def setUp(self):
        super().setUp()

        # For the validity of the test, assert there exist FCirc records and that they are for the last peak groups
        self.assertTrue(self.lss.fcircs.count() > 0)
        for fco in self.lss.fcircs.all():
            self.assertTrue(fco.is_last)

    @classmethod
    def setUpTestData(cls):
        call_command("load_study", "DataRepo/example_data/tissues/loading.yaml")
        call_command(
            "load_compounds",
            compounds="DataRepo/example_data/small_dataset/small_obob_compounds.tsv",
        )
        call_command(
            "load_samples",
            "DataRepo/example_data/small_dataset/small_obob_sample_table_serum_only.tsv",
            sample_table_headers="DataRepo/example_data/sample_table_headers.yaml",
        )
        call_command(
            "load_accucor_msruns",
            protocol="Default",
            accucor_file="DataRepo/example_data/small_dataset/small_obob_maven_6eaas_serum.xlsx",
            date="2021-06-03",
            researcher="Michael Neinast",
            new_researcher=True,
        )

        # Get an animal (assuming it has an infusate/tracers/etc)
        animal = Animal.objects.last()
        # Get its last serum sample
        lss = animal.last_serum_sample

        # Now create a new last serum sample (without any peak groups)
        tissue = lss.tissue
        tc = lss.time_collected + timedelta(seconds=1)
        nlss = Sample.objects.create(
            animal=animal, name=lss.name + "_2", tissue=tissue, time_collected=tc
        )

        cls.lss = lss
        cls.newlss = nlss

        super().setUpTestData()

    def test_new_serum_leaves_is_last_unchanged(self):
        """
        Issue #460, test 3.1.1.
        3. Updates of FCirc.is_last, Sample.is_serum_sample, and Animal.last_serum_sample are triggered by themselves
           and by changes to models down to PeakGroup.
          1. Create a new serum sample whose time collected is later than existing serum samples.
            1. Confirm all FCirc.is_last values are unchanged.
        """
        # Assert that the old last serum sample still has the last tracer peakgroups
        for fco in self.lss.fcircs.all():
            self.assertTrue(fco.is_last)

    def test_new_tracer_peak_group_updates_all_is_last(self):
        """
        Issue #460, test 3.1.1.
        3. Updates of FCirc.is_last, Sample.is_serum_sample, and Animal.last_serum_sample are triggered by themselves
           and by changes to models down to PeakGroup.
          2. Create a new msrun whose date is later than the msrun of the new serum sample (created above), a new
             tracer peak group in the new serum sample (created above), and related peak group labels.
            1. Confirm all FCirc.is_last values related to the old serum sample are now false.
        """

        # Create new protocol, msrun, peak group, and peak group labels
        ptl = Protocol.objects.create(
            name="p1",
            description="p1desc",
            category=Protocol.MSRUN_PROTOCOL,
        )
        msr = MSRun.objects.create(
            researcher="Anakin Skywalker",
            date=datetime.now(),
            sample=self.newlss,
            protocol=ptl,
        )
        pgs = PeakGroupSet.objects.create(filename="testing_dataset_file")
        for tracer in self.lss.animal.infusate.tracers.all():
            pg = PeakGroup.objects.create(
                name=tracer.compound.name,
                formula=tracer.compound.formula,
                msrun=msr,
                peak_group_set=pgs,
            )
            pg.compounds.add(tracer.compound)
            # We don't need to call pg.save() here because I added an m2m handler to make .add() calls trigger a save.
            for label in self.lss.animal.labels.all():
                PeakGroupLabel.objects.create(peak_group=pg, element=label.element)

        # Assert that the old last serum sample's is_last is now false
        for fco in self.lss.fcircs.all():
            # Assert that the method output is correct
            self.assertFalse(fco.is_last_serum_peak_group())
            # Assert that the field was updated
            self.assertFalse(fco.is_last)

        # Create new FCirc records
        for tracer in self.lss.animal.infusate.tracers.all():
            for label in tracer.labels.all():
                FCirc.objects.create(
                    serum_sample=self.newlss, tracer=tracer, element=label.element
                )

        # Assert that the new last serum sample's is_last is true
        for fco in self.newlss.fcircs.all():
            self.assertTrue(fco.is_last)

    def test_maintained_model_relation(self):
        """
        Issue #460, test 4.
        4. Ability to propagate changes without a function decorator if no maintained fields are present

        We will do this by asserting that there's no function decorator for PeakGroup.  If there isn't, and
        test_new_tracer_peak_group_updates_all_is_last passes, then requirement(/test) 4 works.
        """
        maint_fld_funcs = [
            x for x in PeakGroup.get_my_updaters() if x["update_function"] is not None
        ]
        self.assertEqual(
            0,
            len(maint_fld_funcs),
            msg=(
                "No maintained_field_function decorators means that propagation works (if "
                "test_new_tracer_peak_group_updates_all_is_last passes)"
            ),
        )
        maint_mdl_rltns = [
            x for x in PeakGroup.get_my_updaters() if x["update_function"] is None
        ]
        self.assertEqual(
            1,
            len(maint_mdl_rltns),
            msg=(
                "A class maintained_model_relation decorator implies that propagation works (if "
                "test_new_tracer_peak_group_updates_all_is_last passes)"
            ),
        )

    def test_serum_validity_valid(self):
        # Deleting the newlss should make lss valid because the actual last serum sample has peakgroups and the newlss
        # does not.  This depends on autoupdates to update Animal.last_serum_sample
        self.newlss.delete()
        for fcr in self.lss.fcircs.all():
            self.assertTrue(fcr.serum_validity["valid"])
            self.assertIn("No significant problems found", fcr.serum_validity["message"])
            self.assertEqual("good", fcr.serum_validity["level"])
            self.assertEqual("000000000", fcr.serum_validity["bitcode"])

    def test_serum_validity_no_peakgroup(self):
        # Create FCirc records for self.newlss
        for tracer in self.lss.animal.infusate.tracers.all():
            for label in tracer.labels.all():
                FCirc.objects.create(
                    serum_sample=self.newlss, tracer=tracer, element=label.element
                )

        self.assertTrue(self.newlss.fcircs.count() > 0)
        for fcr in self.newlss.fcircs.all():
            print("test_serum_validity_no_peakgroup")
            print(fcr.serum_validity["bitcode"])
            print(fcr.serum_validity["message"])
            self.assertFalse(fcr.serum_validity["valid"])
            self.assertIn("No serum", fcr.serum_validity["message"])
            self.assertEqual("error", fcr.serum_validity["level"])
            self.assertEqual("100000100", fcr.serum_validity["bitcode"])

    def test_serum_validity_no_time_collected(self):
        # When we null the time collected for lss, newlss is still the last serun sample, but the fcirc record for the
        # original lss is still the "last" one with peak groups - because we haven't added any peak groups to newlss
        # for this test

        tcbak = self.lss.time_collected
        self.lss.time_collected = None
        self.lss.save()

        for fcr in self.lss.fcircs.all():
            self.assertFalse(fcr.serum_validity["valid"])
            self.assertIn(
                "The sample time collected is not set for this last serum tracer peak group",
                fcr.serum_validity["message"]
            )
            self.assertEqual("error", fcr.serum_validity["level"])

            # The first 4 bits, explained
            # 0 - no_phgs - lss does have peak groups
            # 1 - stc_many_last - This is the last rec used for fcirc calcs, but there is another serum sample and this
            #                     sample has a null time colelcted
            # 1 - last_ss - This is the last rec used for fcirc calcs, but its serum sample isn't the last serum sample
            # 0 - stc_sibling - The sibling fcirc rec's serum sample has a time collected
            self.assertEqual("011000100", fcr.serum_validity["bitcode"])

        self.lss.time_collected = tcbak
        self.lss.save()

    def test_serum_validity_previous_has_null_time_collected(self):
        tcbak = self.newlss.time_collected
        self.newlss.time_collected = None
        self.newlss.save()

        # Create FCirc records for self.newlss
        for tracer in self.lss.animal.infusate.tracers.all():
            for label in tracer.labels.all():
                FCirc.objects.create(
                    serum_sample=self.newlss, tracer=tracer, element=label.element
                )

        # Now lss is the last serum sample because it has a time_collected, and it has to be used for the FCirc
        # calculations because only it has peak groups, but another serum sample exists with a null time_collected.
        # This creates a warning state.

        self.assertTrue(self.newlss.fcircs.count() > 0)
        for fcr in self.lss.fcircs.all():
            print("test_serum_validity_previous_has_null_time_collected")
            print(fcr.serum_validity["bitcode"])
            print(fcr.serum_validity["message"])
            self.assertTrue(fcr.is_last)
            self.assertFalse(fcr.serum_validity["valid"])
            self.assertIn("may not actually be the last one", fcr.serum_validity["message"])
            self.assertEqual("warn", fcr.serum_validity["level"])
            self.assertEqual("000100100", fcr.serum_validity["bitcode"])

        self.newlss.time_collected = tcbak
        self.newlss.save()

    def test_serum_validity_not_last(self):
        tcbak = self.newlss.time_collected
        self.newlss.time_collected = None
        self.newlss.save()

        # with transaction.atomic():
        # Create new protocol, msrun, peak group, and peak group labels
        ptl = Protocol.objects.create(
            name="p1",
            description="p1desc",
            category=Protocol.MSRUN_PROTOCOL,
        )
        msr = MSRun.objects.create(
            researcher="Anakin Skywalker",
            date=datetime.now(),
            sample=self.newlss,
            protocol=ptl,
        )
        pgs = PeakGroupSet.objects.create(filename="testing_dataset_file")
        for tracer in self.lss.animal.infusate.tracers.all():
            pg = PeakGroup.objects.create(
                name=tracer.compound.name,
                formula=tracer.compound.formula,
                msrun=msr,
                peak_group_set=pgs,
            )
            pg.compounds.add(tracer.compound)
            # We don't need to call pg.save() here because I added an m2m handler to make .add() calls trigger a save.
            for label in self.lss.animal.labels.all():
                PeakGroupLabel.objects.create(peak_group=pg, element=label.element)

        # Create new FCirc records
        for tracer in self.lss.animal.infusate.tracers.all():
            for label in tracer.labels.all():
                FCirc.objects.create(
                    serum_sample=self.newlss, tracer=tracer, element=label.element
                )

        # newlss is the last serum sample and it has peak groups, but lss has to be used for the FCirc
        # calculations because only it has a time_collected.  This creates a warning state.

        self.assertTrue(self.newlss.fcircs.count() > 0)
        for fcr in self.lss.fcircs.all():
            print("test_serum_validity_not_last")
            print(fcr.serum_validity["bitcode"])
            print(fcr.serum_validity["message"])
            self.assertFalse(fcr.serum_validity["valid"])
            self.assertIn("may not actually be the last one", fcr.serum_validity["message"])
            self.assertEqual("warn", fcr.serum_validity["level"])
            self.assertEqual("000100100", fcr.serum_validity["bitcode"])

        self.newlss.time_collected = tcbak
        self.newlss.save()
