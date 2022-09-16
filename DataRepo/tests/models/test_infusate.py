from django.core.management import call_command
from django.test import tag

from DataRepo.management.commands.rebuild_maintained_fields import (
    rebuild_maintained_fields,
)
from DataRepo.models.compound import Compound
from DataRepo.models.infusate import Infusate
from DataRepo.models.infusate_tracer import InfusateTracer
from DataRepo.models.maintained_model import (
    AutoUpdateFailed,
    MaintainedFieldNotSettable,
    buffer_size,
    clear_update_buffer,
    disable_autoupdates,
    enable_autoupdates,
    perform_buffered_updates,
)
from DataRepo.models.tracer import Tracer
from DataRepo.models.tracer_label import TracerLabel
from DataRepo.tests.tracebase_test_case import TracebaseTestCase


def create_infusate_records():
    glu = Compound.objects.create(
        name="glucose", formula="C6H12O6", hmdb_id="HMDB0000122"
    )
    c16 = Compound.objects.create(
        name="C16:0", formula="C16H32O2", hmdb_id="HMDB0000220"
    )
    glu_t = Tracer.objects.create(compound=glu)
    c16_t = Tracer.objects.create(compound=c16)
    TracerLabel.objects.create(
        tracer=glu_t, count=2, element="C", positions=[2, 3], mass_number=13
    )
    TracerLabel.objects.create(
        tracer=glu_t, count=1, element="O", positions=[4], mass_number=17
    )
    TracerLabel.objects.create(
        tracer=c16_t, count=2, element="C", positions=[5, 6], mass_number=13
    )
    TracerLabel.objects.create(tracer=c16_t, count=2, element="O", mass_number=17)
    io = Infusate.objects.create(tracer_group_name="ti")
    InfusateTracer.objects.create(infusate=io, tracer=glu_t, concentration=1.0)
    InfusateTracer.objects.create(infusate=io, tracer=c16_t, concentration=2.0)
    io2 = Infusate.objects.create()
    InfusateTracer.objects.create(infusate=io2, tracer=glu_t, concentration=3.0)
    InfusateTracer.objects.create(infusate=io2, tracer=c16_t, concentration=4.0)

    return io, io2


@tag("multi_working")
class InfusateTests(TracebaseTestCase):
    def setUp(self):
        super().setUp()
        self.INFUSATE1, self.INFUSATE2 = create_infusate_records()

    @classmethod
    def setUpTestData(cls):
        call_command(
            "load_study",
            "DataRepo/example_data/tissues/loading.yaml",
            verbosity=2,
        )
        call_command(
            "load_compounds",
            compounds="DataRepo/example_data/consolidated_tracebase_compound_list.tsv",
            verbosity=2,
        )
        super().setUpTestData()

    def test_infusate_record(self):
        infusate = Infusate.objects.first()
        infusate.full_clean()

    def test_infusate_name_method(self):
        self.assertEqual(
            "ti {C16:0-(5,6-13C2,17O2)[2];glucose-(2,3-13C2,4-17O1)[1]}",
            self.INFUSATE1._name(),
        )
        self.assertEqual(
            "C16:0-(5,6-13C2,17O2)[4];glucose-(2,3-13C2,4-17O1)[3]",
            self.INFUSATE2._name(),
        )

    def test_name_not_settable(self):
        with self.assertRaises(MaintainedFieldNotSettable):
            Infusate.objects.create(
                name="test infusate",
                tracer_group_name="ti2",
            )

    def test_name_autoupdated(self):
        """
        Make sure that the name field was set automatically - triggered by the InfusateTracer record creation.
        """
        # Throws DoesNotExist exception if not found
        Infusate.objects.get(
            name="ti {C16:0-(5,6-13C2,17O2)[2];glucose-(2,3-13C2,4-17O1)[1]}"
        )

    def test_name_none(self):
        """
        Make sure that the name field was set automatically - triggered by the InfusateTracer record creation.
        """
        self.assertEqual(
            "C16:0-(5,6-13C2,17O2)[4];glucose-(2,3-13C2,4-17O1)[3]",
            self.INFUSATE2.name,
        )
        # Throws DoesNotExist exception if not found
        Infusate.objects.get(
            name__exact="C16:0-(5,6-13C2,17O2)[4];glucose-(2,3-13C2,4-17O1)[3]"
        )

    def test_name_self_autoupdated(self):
        """
        Make sure that the name field was set automatically - triggered by the Infusate record creation.
        """
        ti3 = Infusate.objects.create(tracer_group_name="ti3")
        self.assertEqual("ti3", ti3.name)
        # Throws DoesNotExist exception if not found
        Infusate.objects.get(name="ti3")

    def test_delete_autoupdate(self):
        """
        Make sure parent records are updated when a child record is deleted
        """
        tl = TracerLabel.objects.get(name="2,3-13C2")
        tl.delete()
        # get fresh objects
        i1 = Infusate.objects.get(id__exact=self.INFUSATE1.id)
        i2 = Infusate.objects.get(id__exact=self.INFUSATE2.id)
        # The deletion affects the tracer name (which should have been autoupdated)
        self.assertEqual("glucose-(4-17O1)", tl.tracer.name)
        # The deletion also affects the names of both infusates that had that tracer
        self.assertEqual("ti {C16:0-(5,6-13C2,17O2)[2];glucose-(4-17O1)[1]}", i1.name)
        self.assertEqual("C16:0-(5,6-13C2,17O2)[4];glucose-(4-17O1)[3]", i2.name)


@tag("multi_working")
class MaintainedModelTests(TracebaseTestCase):
    def setUp(self):
        super().setUp()
        # Each test first reruns the setup and the DB load adds the same records to the buffer. The DB is emptied after
        # the test runs, but the buffer needs to be explicitly emptied
        clear_update_buffer()
        disable_autoupdates()
        create_infusate_records()
        enable_autoupdates()

    @classmethod
    def setUpTestData(cls):
        call_command(
            "load_study",
            "DataRepo/example_data/tissues/loading.yaml",
            verbosity=2,
        )
        call_command(
            "load_compounds",
            compounds="DataRepo/example_data/consolidated_tracebase_compound_list.tsv",
            verbosity=2,
        )
        super().setUpTestData()

    def test_nullable(self):
        """
        MaintainedModel doesn't require the update_field be nullable, but it helps to make the
        test_disabled_autoupdates test straightforward
        """
        self.assertTrue(TracerLabel._meta.get_field("name").null)
        self.assertTrue(Tracer._meta.get_field("name").null)
        self.assertTrue(Infusate._meta.get_field("name").null)

    def test_disabled_autoupdates(self):
        """
        Makes sure name is not autoupdated in TracerLabel, Tracer, nor Infusate
        """
        self.assertIsNone(TracerLabel.objects.first().name)
        self.assertIsNone(Tracer.objects.first().name)
        self.assertIsNone(Infusate.objects.first().name)

    def test_mass_autoupdate(self):
        """
        Ensures that the name fields were all updated, updated correctly, and the buffer emptied.
        """
        disable_autoupdates()  # Required for buffered updates to prevent DFS update behavior
        perform_buffered_updates()
        # Ensure all the auto-updated fields not have values (correctness of values tested elsewhere)
        for tl in TracerLabel.objects.all():
            self.assertIsNotNone(tl.name)
            self.assertEqual(tl.name, tl._name())
        for t in Tracer.objects.all():
            self.assertIsNotNone(t.name)
            self.assertEqual(t.name, t._name())
        for i in Infusate.objects.all():
            self.assertIsNotNone(i.name)
            self.assertEqual(i.name, i._name())
        # Ensure the buffer was emptied by perform_buffered_updates
        self.assertEqual(buffer_size(), 0)
        enable_autoupdates()

    def test_enable_autoupdates(self):
        """
        Ensures that the name field was constructed.
        """
        enable_autoupdates()
        lys = Compound.objects.create(name="lysine2", formula="C6H14N2O2", hmdb_id=3)
        Tracer.objects.create(compound=lys)
        Tracer.objects.get(name="lysine2")

    def test_buffer_cleared_after_sample_load(self):
        """Ensure the sample load doesn't leave stuff in the buffer when it exits successfully"""
        # The sample load only auto-updates fields with the "name" label in the decorator, so the sample_table_loader
        # must clear the buffer when it ends successfully
        call_command(
            "load_animals_and_samples",
            animal_and_sample_table_filename=(
                "DataRepo/example_data/small_dataset/"
                "small_obob_animal_and_sample_table.xlsx"
            ),
            debug=False,
        )
        self.assertEqual(0, buffer_size())
        # TODO: Create a feature issue to tell the auto-update code to only buffer records with matching labels

    def test_error_when_buffer_not_clear(self):
        """Ensure that stale buffer contents before a load produces a helpful error"""
        disable_autoupdates()
        # Create infusate records while auto updates are disabled, so that they buffer
        infusate1, infusate2 = create_infusate_records()
        # Delete the records and do not clear the buffer
        infusate1.delete()
        infusate2.delete()
        enable_autoupdates()
        with self.assertRaisesRegex(AutoUpdateFailed, ".+clear_update_buffer.+"):
            call_command(
                "load_animals_and_samples",
                animal_and_sample_table_filename=(
                    "DataRepo/example_data/small_dataset/"
                    "small_obob_animal_and_sample_table.xlsx"
                ),
                debug=False,
            )
        # Now clean up the buffer
        clear_update_buffer()


@tag("multi_working")
class RebuildMaintainedModelFieldsTests(TracebaseTestCase):
    def setUp(self):
        super().setUp()
        # Each test first reruns the setup and the DB load adds the same records to the buffer. The DB is emptied after
        # the test runs, but the buffer needs to be explicitly emptied
        disable_autoupdates()
        create_infusate_records()
        enable_autoupdates()

    def test_rebuild_maintained_fields(self):
        rebuild_maintained_fields()
        # Ensure all the auto-updated fields not have values (correctness of values tested elsewhere)
        for i in Infusate.objects.all():
            self.assertIsNotNone(i.name)
            self.assertEqual(i.name, i._name())
        for t in Tracer.objects.all():
            self.assertIsNotNone(t.name)
            self.assertEqual(t.name, t._name())
        for tl in TracerLabel.objects.all():
            self.assertIsNotNone(tl.name)
            self.assertEqual(tl.name, tl._name())
        # Ensure the buffer was emptied by perform_buffered_updates
        self.assertEqual(buffer_size(), 0)
