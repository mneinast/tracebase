from django.core.management import call_command
from django.test import TestCase

from DataRepo.compositeviews import BaseAdvancedSearchView, BaseSearchView
from DataRepo.models import PeakGroup


class CompositeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "tissues.yaml")
        call_command(
            "load_compounds",
            compounds="DataRepo/example_data/small_dataset/small_obob_compounds.tsv",
        )
        call_command(
            "load_samples",
            "DataRepo/example_data/small_dataset/small_obob_sample_table.tsv",
            sample_table_headers="DataRepo/example_data/sample_table_headers.yaml",
        )
        call_command(
            "load_samples",
            "DataRepo/example_data/small_dataset/small_obob_sample_table_2ndstudy.tsv",
            sample_table_headers="DataRepo/example_data/sample_table_headers.yaml",
        )
        call_command(
            "load_accucor_msruns",
            protocol="Default",
            accucor_file="DataRepo/example_data/small_dataset/small_obob_maven_6eaas_inf.xlsx",
            date="2021-06-03",
            researcher="Michael Neinast",
            new_researcher=True,
        )
        call_command(
            "load_accucor_msruns",
            protocol="Default",
            accucor_file="DataRepo/example_data/small_dataset/small_obob_maven_6eaas_serum.xlsx",
            date="2021-06-03",
            researcher="Michael Neinast",
            new_researcher=False,
        )

    def getQueryObject(self):
        return {
            "selectedtemplate": "pgtemplate",
            "searches": {
                "pgtemplate": {
                    "tree": {
                        "type": "group",
                        "val": "all",
                        "static": False,
                        "queryGroup": [
                            {
                                "type": "query",
                                "pos": "",
                                "static": False,
                                "ncmp": "icontains",
                                "fld": "msrun__sample__animal__studies__name",
                                "val": "obob_fasted",
                            }
                        ],
                    },
                    "name": "PeakGroups",
                },
                "pdtemplate": {"name": "PeakData", "tree": {}},
                "fctemplate": {"name": "Fcirc", "tree": {}},
            },
        }

    def test_getMMKeyPaths(self):
        basv = BaseAdvancedSearchView()
        result = basv.getMMKeyPaths("pdtemplate")
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == "peak_group__msrun__sample__animal__studies")

    def test_shouldReFilter_true(self):
        """
        Test that we should refilter if the query includes a term from a M:M related table
        """
        qry = self.getQueryObject()
        basv = BaseAdvancedSearchView()
        result = basv.shouldReFilter(qry)
        self.assertTrue(result)

    def test_shouldReFilter_false(self):
        """
        Test that we should not refilter if the query does not include a term from a M:M related table
        """
        qry = self.getQueryObject()
        qry["searches"]["pgtemplate"]["tree"]["queryGroup"][0]["ncmp"] = "icontains"
        qry["searches"]["pgtemplate"]["tree"]["queryGroup"][0][
            "fld"
        ] = "msrun__sample__animal__name"
        qry["searches"]["pgtemplate"]["tree"]["queryGroup"][0]["val"] = "anything"
        basv = BaseAdvancedSearchView()
        result = basv.shouldReFilter(qry)
        self.assertTrue(not result)

    def test_isAMatch(self):
        basv = BaseAdvancedSearchView()
        qry = self.getQueryObject()
        pgrecs = PeakGroup.objects.filter(
            msrun__sample__animal__studies__name__icontains="obob_fasted"
        )
        studyrecs = pgrecs[0].msrun.sample.animal.studies.all()
        mm_lookup = {"msrun__sample__animal__studies": studyrecs[0]}
        result = basv.isAMatch(pgrecs, mm_lookup, qry)
        self.assertTrue(result)
        mm_lookup["msrun__sample__animal__studies"] = studyrecs[1]
        result = basv.isAMatch(pgrecs, mm_lookup, qry)
        self.assertTrue(not result)

    def test_getFldValues(self):
        qry = self.getQueryObject()
        bsv = BaseSearchView()
        result = bsv.getFldValues(qry["searches"]["pgtemplate"]["tree"])
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == "msrun__sample__animal__studies__name")

    def test_getValue(self):
        bsv = BaseSearchView()
        pgrecs = PeakGroup.objects.filter(
            msrun__sample__animal__studies__name__icontains="obob_fasted"
        )
        studyrecs = pgrecs[0].msrun.sample.animal.studies.all()
        mm_lookup = {"msrun__sample__animal__studies": studyrecs[0]}
        result = bsv.getValue(
            pgrecs[0], mm_lookup, "msrun__sample__animal__studies__name"
        )
        self.assertTrue(studyrecs[0].name == "obob_fasted")
        self.assertTrue(result == "obob_fasted")

    def test_getMMKeyPathList(self):
        bsv = BaseSearchView()

        # test a M:M related table query key path
        qry_keypath = "msrun__sample__animal__studies__name"
        pgrecs = PeakGroup.objects.filter(
            msrun__sample__animal__studies__name__icontains="obob_fasted"
        )
        studyrecs = pgrecs[0].msrun.sample.animal.studies.all()
        mm_lookup = {"msrun__sample__animal__studies": studyrecs[0]}
        rec, qkpl = bsv.getMMKeyPathList(qry_keypath, mm_lookup, pgrecs[0])
        self.assertTrue(rec == studyrecs[0])
        self.assertTrue(len(qkpl) == 1)
        self.assertTrue(qkpl[0] == "name")

        # Test a non-M:M related table query key path
        qry_keypath = "msrun__sample__animal__name"
        rec, qkpl = bsv.getMMKeyPathList(qry_keypath, mm_lookup, pgrecs[0])
        self.assertTrue(rec == pgrecs[0])
        self.assertTrue(len(qkpl) == 4)
        self.assertTrue(qkpl[0] == "msrun")
        self.assertTrue(qkpl[1] == "sample")
        self.assertTrue(qkpl[2] == "animal")
        self.assertTrue(qkpl[3] == "name")

    def test_valueMatches(self):
        bsv = BaseSearchView()
        recval = "abcDefg"
        condition = "icontains"
        term = "cde"
        bsv.valueMatches(recval, condition, term)