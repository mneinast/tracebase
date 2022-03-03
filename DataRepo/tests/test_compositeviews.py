from copy import deepcopy

from django.core.management import call_command

from DataRepo.compositeviews import (
    BaseAdvancedSearchView,
    PeakGroupsSearchView,
    extractFldPaths,
    splitCommon,
    splitPathName,
)
from DataRepo.tests.tracebase_test_case import TracebaseTestCase


class CompositeViewTests(TracebaseTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_study", "DataRepo/example_data/tissues/loading.yaml")
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

    def getQueryObject2(self):
        qry = deepcopy(self.getQueryObject())
        qry["searches"]["pgtemplate"]["tree"]["queryGroup"].append(
            {
                "type": "query",
                "pos": "",
                "static": False,
                "ncmp": "icontains",
                "fld": "compounds__synonyms__name",
                "val": "glucose",
            }
        )
        return qry

    def getPdtemplateChoicesTuple(self):
        return (
            ("peak_group__msrun__sample__animal__name", "Animal"),
            ("peak_group__msrun__sample__animal__body_weight", "Body Weight (g)"),
            ("corrected_abundance", "Corrected Abundance"),
            ("peak_group__msrun__sample__animal__diet", "Diet"),
            ("peak_group__msrun__sample__animal__feeding_status", "Feeding Status"),
            ("peak_group__formula", "Formula"),
            ("peak_group__msrun__sample__animal__genotype", "Genotype"),
            ("labeled_count", "Labeled Count"),
            ("labeled_element", "Labeled Element"),
            (
                "peak_group__compounds__synonyms__name",
                "Measured Compound (Any Synonym)",
            ),
            ("peak_group__compounds__name", "Measured Compound (Primary Synonym)"),
            ("med_mz", "Median M/Z"),
            ("med_rt", "Median RT"),
            ("peak_group__name", "Peak Group"),
            ("peak_group__peak_group_set__filename", "Peak Group Set Filename"),
            ("raw_abundance", "Raw Abundance"),
            ("peak_group__msrun__sample__name", "Sample"),
            ("peak_group__msrun__sample__animal__sex", "Sex"),
            ("peak_group__msrun__sample__animal__studies__name", "Study"),
            ("peak_group__msrun__sample__tissue__name", "Tissue"),
            (
                "peak_group__msrun__sample__animal__tracer_compound__name",
                "Tracer Compound (Primary Synonym)",
            ),
            (
                "peak_group__msrun__sample__animal__tracer_infusion_concentration",
                "Tracer Infusion Concentration (mM)",
            ),
            (
                "peak_group__msrun__sample__animal__tracer_infusion_rate",
                "Tracer Infusion Rate (ul/min/g)",
            ),
            ("peak_group__msrun__sample__animal__treatment__name", "Treatment"),
        )

    def getPgtemplateChoicesTuple(self):
        return (
            ("msrun__sample__animal__name", "Animal"),
            ("msrun__sample__animal__body_weight", "Body Weight (g)"),
            ("msrun__sample__animal__diet", "Diet"),
            ("msrun__sample__animal__feeding_status", "Feeding Status"),
            ("formula", "Formula"),
            ("msrun__sample__animal__genotype", "Genotype"),
            ("compounds__synonyms__name", "Measured Compound (Any Synonym)"),
            ("compounds__name", "Measured Compound (Primary Synonym)"),
            ("name", "Peak Group"),
            ("peak_group_set__filename", "Peak Group Set Filename"),
            ("msrun__sample__name", "Sample"),
            ("msrun__sample__animal__sex", "Sex"),
            ("msrun__sample__animal__studies__name", "Study"),
            ("msrun__sample__tissue__name", "Tissue"),
            (
                "msrun__sample__animal__tracer_compound__name",
                "Tracer Compound (Primary Synonym)",
            ),
            (
                "msrun__sample__animal__tracer_infusion_concentration",
                "Tracer Infusion Concentration (mM)",
            ),
            (
                "msrun__sample__animal__tracer_infusion_rate",
                "Tracer Infusion Rate (ul/min/g)",
            ),
            ("msrun__sample__animal__tracer_labeled_atom", "Tracer Labeled Element"),
            ("msrun__sample__animal__treatment__name", "Treatment"),
        )

    def test_getSearchFieldChoicesDict(self):
        basv = BaseAdvancedSearchView()
        sfcd = basv.getSearchFieldChoicesDict()
        sfcd_expected = {
            "fctemplate": (
                ("msrun__sample__animal__name", "Animal"),
                ("msrun__sample__animal__body_weight", "Body Weight (g)"),
                ("msrun__sample__animal__diet", "Diet"),
                ("msrun__sample__animal__feeding_status", "Feeding Status"),
                ("msrun__sample__animal__genotype", "Genotype"),
                ("msrun__sample__animal__sex", "Sex"),
                ("msrun__sample__animal__studies__name", "Study"),
                (
                    "msrun__sample__time_collected",
                    "Time Collected (hh:mm:ss since infusion)",
                ),
                ("msrun__sample__animal__tracer_compound__name", "Tracer Compound"),
                (
                    "msrun__sample__animal__tracer_infusion_concentration",
                    "Tracer Infusion Concentration (mM)",
                ),
                (
                    "msrun__sample__animal__tracer_infusion_rate",
                    "Tracer Infusion Rate (ul/min/g)",
                ),
                (
                    "msrun__sample__animal__tracer_labeled_atom",
                    "Tracer Labeled Element",
                ),
                ("msrun__sample__animal__treatment__name", "Treatment"),
            ),
            "pdtemplate": self.getPdtemplateChoicesTuple(),
            "pgtemplate": self.getPgtemplateChoicesTuple(),
        }
        self.assertDictEqual(sfcd, sfcd_expected)

    def test_getAllSearchFieldChoices(self):
        basv = BaseAdvancedSearchView()
        sfct = basv.getAllSearchFieldChoices()
        sfct_expected = self.getPgtemplateChoicesTuple()
        sfct_expected += self.getPdtemplateChoicesTuple()
        sfct_expected += (
            (
                "msrun__sample__time_collected",
                "Time Collected (hh:mm:ss since infusion)",
            ),
        )
        self.assertTupleEqual(sfct, sfct_expected)

    def test_extractFldPaths(self):
        paths = extractFldPaths(self.getQueryObject())
        expected_paths = ["msrun__sample__animal__studies"]
        self.assertEqual(paths, expected_paths)

    def test_splitCommon_hascommon(self):
        fld_path = "msrun__sample__animal__studies"
        reroot_path = "msrun__sample__animal__tracer_compound"
        common_path, remainder = splitCommon(fld_path, reroot_path)
        self.assertEqual(common_path, "msrun__sample__animal")
        self.assertEqual(remainder, "studies")

    def test_splitCommon_nocommon(self):
        fld_path = "msrun__sample__animal__studies"
        reroot_path = "compounds__synonyms"
        common_path, remainder = splitCommon(fld_path, reroot_path)
        self.assertEqual(common_path, "")
        self.assertEqual(remainder, "msrun__sample__animal__studies")

    def test_splitPathName(self):
        path, name = splitPathName("msrun__sample__animal__treatment__name")
        self.assertEqual(path, "msrun__sample__animal__treatment")
        self.assertEqual(name, "name")

    def test_reRootFieldPath(self):
        fld = "msrun__sample__animal__studies__name"
        reroot_instance_name = "CompoundSynonym"
        pgsv = PeakGroupsSearchView()
        rerooted_fld = pgsv.reRootFieldPath(fld, reroot_instance_name)
        expected_fld = "compound__peak_groups__msrun__sample__animal__studies__name"
        self.assertEqual(rerooted_fld, expected_fld)

    def test_reRootQry(self):
        qry = self.getQueryObject2()
        qry_backup = deepcopy(qry)
        basv = BaseAdvancedSearchView()
        new_qry = basv.reRootQry("pgtemplate", qry, "MeasuredCompound")
        expected_qry = deepcopy(self.getQueryObject2())
        expected_qry["searches"]["pgtemplate"]["tree"]["queryGroup"][0][
            "fld"
        ] = "peak_groups__msrun__sample__animal__studies__name"
        expected_qry["searches"]["pgtemplate"]["tree"]["queryGroup"][1][
            "fld"
        ] = "synonyms__name"
        self.assertEqual(qry, qry_backup, msg="qry must be left unchanged")
        self.assertEqual(new_qry, expected_qry)

    def test_pathToModelInstanceName(self):
        pgsv = PeakGroupsSearchView()
        mi = pgsv.pathToModelInstanceName("msrun__sample__animal__studies")
        self.assertEqual(mi, "Study")

    def test_getTrueJoinPrefetchPathsAndQrys(self):
        qry = self.getQueryObject2()
        basv = BaseAdvancedSearchView()
        prefetches = basv.getTrueJoinPrefetchPathsAndQrys(qry)
        expected_prefetches = [
            "msrun__sample__animal__tracer_compound",
            "msrun__sample__animal__treatment",
            [
                "msrun__sample__animal__studies",
                {
                    "searches": {
                        "fctemplate": {
                            "name": "Fcirc",
                            "tree": {},
                        },
                        "pdtemplate": {
                            "name": "PeakData",
                            "tree": {},
                        },
                        "pgtemplate": {
                            "name": "PeakGroups",
                            "tree": {
                                "queryGroup": [
                                    {
                                        "fld": "name",
                                        "ncmp": "icontains",
                                        "pos": "",
                                        "static": False,
                                        "type": "query",
                                        "val": "obob_fasted",
                                    },
                                    {
                                        "fld": "animals__samples__msruns__peak_groups__compounds__synonyms__name",
                                        "ncmp": "icontains",
                                        "pos": "",
                                        "static": False,
                                        "type": "query",
                                        "val": "glucose",
                                    },
                                ],
                                "static": False,
                                "type": "group",
                                "val": "all",
                            },
                        },
                    },
                    "selectedtemplate": "pgtemplate",
                },
                "Study",
            ],
            "msrun__sample__tissue",
            [
                "compounds__synonyms",
                {
                    "searches": {
                        "fctemplate": {
                            "name": "Fcirc",
                            "tree": {},
                        },
                        "pdtemplate": {
                            "name": "PeakData",
                            "tree": {},
                        },
                        "pgtemplate": {
                            "name": "PeakGroups",
                            "tree": {
                                "queryGroup": [
                                    {
                                        "fld": "compound__peak_groups__msrun__sample__animal__studies__name",
                                        "ncmp": "icontains",
                                        "pos": "",
                                        "static": False,
                                        "type": "query",
                                        "val": "obob_fasted",
                                    },
                                    {
                                        "fld": "name",
                                        "ncmp": "icontains",
                                        "pos": "",
                                        "static": False,
                                        "type": "query",
                                        "val": "glucose",
                                    },
                                ],
                                "static": False,
                                "type": "group",
                                "val": "all",
                            },
                        },
                    },
                    "selectedtemplate": "pgtemplate",
                },
                "CompoundSynonym",
            ],
            "peak_group_set",
        ]

        self.assertEqual(prefetches, expected_prefetches)
