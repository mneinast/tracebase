from datetime import datetime

import pandas as pd
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase

from .models import (
    Animal,
    Compound,
    MSRun,
    PeakData,
    PeakGroup,
    Protocol,
    Sample,
    Study,
    Tissue,
    TracerLabeledClass,
)
from .utils import AccuCorDataLoader


class ExampleDataConsumer:
    def get_sample_test_dataframe(self):

        # making this a dataframe, if more rows are need for future tests, or we
        # switch to a file based test
        test_df = pd.DataFrame(
            {
                "Sample Name": ["bat-xz969"],
                "Date Collected": ["2020-11-18"],
                "Researcher Name": ["Xianfeng Zhang"],
                "Tissue": ["BAT"],
                "Animal ID": ["969"],
                "Animal Genotype": ["WT"],
                "Animal Body Weight": ["27.2"],
                "Tracer Compound": ["C16:0"],
                "Tracer Labeled Atom": ["C"],
                "Tracer Label Atom Count": ["16.00"],
                "Tracer Infusion Rate": ["0.55"],
                "Tracer Concentration": ["8.00"],
                "Animal State": ["Fasted"],
                "Study Name": ["obob_fasted"],
            }
        )
        return test_df

    def get_peak_group_test_dataframe(self):

        peak_data_df = pd.DataFrame(
            {
                "labeled_element": ["C", "C"],
                "labeled_count": [0, 1],
                "raw_abundance": [187608.7, 11873.74],
                "corrected_abundance": [203286.917004701, 0],
                "med_mz": [179.0558, 180.0592],
                "med_rt": [11.22489, 11.21671],
            }
        )
        peak_group_df = pd.DataFrame(
            {"name": ["glucose"], "formula": ["C6H12O6"], "peak_data": [peak_data_df]}
        )
        return peak_group_df


class CompoundTests(TestCase):
    def setUp(self):
        Compound.objects.create(
            name="alanine", formula="C3H7NO2", hmdb_id="HMDB0000161"
        )

    def test_compound_name(self):
        """Compound lookup by name"""
        alanine = Compound.objects.get(name="alanine")
        self.assertEqual(alanine.name, "alanine")

    def test_compound_hmdb_url(self):
        """Compound hmdb url"""
        alanine = Compound.objects.get(name="alanine")
        self.assertEqual(alanine.hmdb_url, f"{Compound.HMDB_CPD_URL}/{alanine.hmdb_id}")

    def test_compound_atom_count(self):
        """Compound atom_count"""
        alanine = Compound.objects.get(name="alanine")
        self.assertEqual(alanine.atom_count("C"), 3)

    def test_compound_atom_count_zero(self):
        """Compound atom_count"""
        alanine = Compound.objects.get(name="alanine")
        self.assertEqual(alanine.atom_count("F"), 0)

    def test_compound_atom_count_invalid(self):
        """Compound atom_count"""
        alanine = Compound.objects.get(name="alanine")
        with self.assertWarns(UserWarning):
            self.assertEqual(alanine.atom_count("Abc"), None)


class StudyTests(TestCase, ExampleDataConsumer):
    def setUp(self):
        # Get test data
        self.testdata = self.get_sample_test_dataframe()
        first = self.testdata.iloc[0]
        self.first = first

        # Create animal with tracer
        self.tracer = Compound.objects.create(name=first["Tracer Compound"])
        self.animal = Animal.objects.create(
            name=first["Animal ID"],
            state=first["Animal State"],
            body_weight=first["Animal Body Weight"],
            genotype=first["Animal Genotype"],
            tracer_compound=self.tracer,
            tracer_labeled_atom=first["Tracer Labeled Atom"],
            tracer_labeled_count=int(float(first["Tracer Label Atom Count"])),
            tracer_infusion_rate=first["Tracer Infusion Rate"],
            tracer_infusion_concentration=first["Tracer Concentration"],
        )

        # Create a sample from the animal
        self.tissue = Tissue.objects.create(name=first["Tissue"])
        self.sample = Sample.objects.create(
            name=first["Sample Name"],
            tissue=self.tissue,
            animal=self.animal,
            researcher=first["Researcher Name"],
            date=first["Date Collected"],
        )

        self.protocol = Protocol.objects.create(name="p1", description="p1desc")
        self.msrun = MSRun.objects.create(
            researcher="John Doe",
            date=datetime.now(),
            protocol=self.protocol,
            sample=self.sample,
        )

        self.peak_group_df = self.get_peak_group_test_dataframe()
        initial_peak_group = self.peak_group_df.iloc[0]
        self.peak_group = PeakGroup.objects.create(
            name=initial_peak_group["name"],
            formula=initial_peak_group["formula"],
            ms_run=self.msrun,
        )
        # actual code would have to more careful in retrieving compounds based
        # on the data's peak_group name
        compound_fk = Compound.objects.create(
            name=self.peak_group.name,
            formula=self.peak_group.formula,
            hmdb_id="HMDB0000122",
        )
        self.peak_group.compounds.add(compound_fk)
        self.peak_group.save()

        initial_peak_data_df = initial_peak_group["peak_data"]
        for index, row in initial_peak_data_df.iterrows():
            model = PeakData()
            model.peak_group = self.peak_group
            model.labeled_element = row["labeled_element"]
            model.labeled_count = row["labeled_count"]
            model.raw_abundance = row["raw_abundance"]
            model.corrected_abundance = row["corrected_abundance"]
            model.med_mz = row["med_mz"]
            model.med_rt = row["med_rt"]
            model.save()

    def test_tracer(self):
        self.assertEqual(self.tracer.name, self.first["Tracer Compound"])

    def test_tissue(self):
        self.assertEqual(self.tissue.name, self.first["Tissue"])

    def test_animal(self):
        self.assertEqual(self.animal.name, self.first["Animal ID"])
        self.assertEqual(
            self.animal.tracer_compound.name, self.first["Tracer Compound"]
        )

    def test_study(self):
        """create study and associate animal"""
        # Create a study
        study = Study.objects.create(name=self.first["Study Name"])
        self.assertEqual(study.name, self.first["Study Name"])

        # add the animal to the study
        study.animals.add(self.animal)
        self.assertEqual(study.animals.get().name, self.animal.name)

    def test_sample(self):
        # Test sample relations
        self.assertEqual(self.sample.name, self.first["Sample Name"])
        self.assertEqual(self.sample.tissue.name, self.first["Tissue"])
        self.assertEqual(self.sample.animal.name, self.first["Animal ID"])

    def test_msrun_protocol(self):
        """MSRun lookup by primary key"""
        msr = MSRun.objects.get(id=self.msrun.pk)
        self.assertEqual(msr.protocol.name, "p1")

    def test_peak_group(self):
        t_peak_group = PeakGroup.objects.get(name=self.peak_group.name)
        self.assertEqual(t_peak_group.peak_data.count(), 2)
        self.assertEqual(t_peak_group.name, self.peak_group.name)

    def test_peak_group_atom_count(self):
        """PeakGroup atom_count"""
        t_peak_group = PeakGroup.objects.get(name=self.peak_group.name)
        self.assertEqual(t_peak_group.atom_count("C"), 6)

    def test_peak_group_unique_constraint(self):
        self.assertRaises(
            IntegrityError,
            lambda: PeakGroup.objects.create(
                name=self.peak_group.name, ms_run=self.msrun
            ),
        )


class DataLoadingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_compounds", "DataRepo/example_data/obob_compounds.tsv")
        call_command(
            "load_samples",
            "DataRepo/example_data/obob_sample_table.tsv",
            sample_table_headers="DataRepo/example_data/obob_sample_table_headers.yaml",
        )
        call_command(
            "load_accucor_msruns",
            protocol="Default",
            accucor_file="DataRepo/example_data/obob_maven_6eaas_inf.xlsx",
            date="2021-04-29",
            researcher="Michael",
        )
        call_command(
            "load_accucor_msruns",
            protocol="Default",
            accucor_file="DataRepo/example_data/obob_maven_6eaas_serum.xlsx",
            date="2021-04-29",
            researcher="Michael",
        )

    def test_compounds_loaded(self):
        self.assertEqual(Compound.objects.all().count(), 32)

    def test_samples_loaded(self):
        # if we discount the header and the 2 blank samples, there should be 106
        self.assertEqual(Sample.objects.all().count(), 106)

        # if we discount the header and the BLANK animal, there should be 7
        ANIMALS_COUNT = 7
        self.assertEqual(Animal.objects.all().count(), ANIMALS_COUNT)

        self.assertEqual(Study.objects.all().count(), 1)

        # and the animals should be in the study
        study = Study.objects.get(name="obob_fasted")
        self.assertEqual(study.animals.count(), ANIMALS_COUNT)

    def test_animal_tracers(self):
        a = Animal.objects.get(name="969")
        c = Compound.objects.get(name="C16:0")
        self.assertEqual(a.tracer_compound, c)
        self.assertEqual(a.tracer_labeled_atom, TracerLabeledClass.CARBON)
        self.assertEqual(a.sex, None)

    def test_peak_groups_loaded(self):
        # inf data file: 7 compounds and 56 samples, 7 * 56 = 392
        # serum data file: 13 compounds and 4 samples, 13 * 4 = 52
        self.assertEqual(PeakGroup.objects.all().count(), 392 + 52)

    def test_peak_data_loaded(self):
        # inf data file: 38 PeakData rows for 56 samples, 38 * 60 = 2128
        # serum data file: 85 PeakData rows for 4 samples, 85 * 4 = 340
        self.assertEqual(PeakData.objects.all().count(), 2128 + 340)

    def test_peak_group_peak_data_1(self):
        peak_group = (
            PeakGroup.objects.filter(compounds__name="glucose")
            .filter(ms_run__sample__name="BAT-xz971")
            .get()
        )
        peak_data = peak_group.peak_data.filter(labeled_count=0).get()
        self.assertEqual(peak_data.raw_abundance, 8814287)
        self.assertAlmostEqual(peak_data.corrected_abundance, 9553199.89089051)

    def test_peak_group_peak_data_2(self):
        peak_group = (
            PeakGroup.objects.filter(compounds__name="histidine")
            .filter(ms_run__sample__name="serum-xz971")
            .get()
        )
        # There should be a peak_data for each label count 0-6
        self.assertEqual(peak_group.peak_data.count(), 7)
        # The peak_data for labeled_count==2 is missing, thus values should be 0
        peak_data = peak_group.peak_data.filter(labeled_count=2).get()
        self.assertEqual(peak_data.raw_abundance, 0)
        self.assertEqual(peak_data.med_mz, 0)
        self.assertEqual(peak_data.med_rt, 0)
        self.assertEqual(peak_data.corrected_abundance, 0)

    def test_peak_group_peak_data_3(self):
        peak_group = (
            PeakGroup.objects.filter(compounds__name="histidine")
            .filter(ms_run__sample__name="serum-xz971")
            .get()
        )
        peak_data = peak_group.peak_data.filter(labeled_count=5).get()
        self.assertAlmostEqual(peak_data.raw_abundance, 1356.587)
        self.assertEqual(peak_data.corrected_abundance, 0)


class AccuCorDataLoaderTests(TestCase):
    def test_parse_parent_isotope_label(self):
        self.assertEqual(
            AccuCorDataLoader.parse_isotope_label("C12 PARENT"), ("C12", 0)
        )

    def test_parse_isotope_label(self):
        self.assertEqual(
            AccuCorDataLoader.parse_isotope_label("C13-label-5"), ("C13", 5)
        )

    def test_parse_isotope_label_bad(self):
        with self.assertRaises(ValueError):
            AccuCorDataLoader.parse_isotope_label("label-5")

    def test_parse_isotope_label_empty(self):
        with self.assertRaises(ValueError):
            AccuCorDataLoader.parse_isotope_label("")

    def test_parse_isotope_label_none(self):
        with self.assertRaises(TypeError):
            AccuCorDataLoader.parse_isotope_label(None)
