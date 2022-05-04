from DataRepo.formats.dataformat import Format
from DataRepo.formats.dataformat_group_query import (
    appendFilterToGroup,
    createFilterCondition,
    createFilterGroup,
)
from DataRepo.models import Animal, PeakData, TracerLabeledClass


class PeakDataFormat(Format):
    """
    This class encapsulates all the metadata of a single search output format, which includes multiple tables/fields.
    """

    id = "pdtemplate"
    name = "PeakData"
    rootmodel = PeakData
    stats = [
        {
            "displayname": "Animals",
            "distincts": ["peak_group__msrun__sample__animal__name"],
            "filter": None,
        },
        {
            "displayname": "Labels",
            "distincts": [
                "labeled_element",
                "labeled_count",
            ],
            "filter": None,
            "delimiter": ":",
        },
        {
            "displayname": "Feeding Statuses",
            "distincts": ["peak_group__msrun__sample__animal__feeding_status"],
            "filter": None,
        },
        {
            "displayname": "Corrected Abundances",  # Append " > 0.1" based on filter
            "distincts": ["corrected_abundance"],
            "filter": appendFilterToGroup(
                createFilterGroup(),
                createFilterCondition("corrected_abundance", "gt", 0.1),
            ),
        },
        {
            "displayname": "Samples",
            "distincts": ["peak_group__msrun__sample__name"],
            "filter": None,
        },
        {
            "displayname": "Tissues",
            "distincts": ["peak_group__msrun__sample__tissue__name"],
            "filter": None,
        },
        {
            "displayname": "Tracer Compounds",
            "distincts": ["peak_group__msrun__sample__animal__tracer_compound__name"],
            "filter": None,
        },
        {
            "displayname": "Measured Compounds",
            "distincts": ["peak_group__compounds__name"],
            "filter": None,
        },
    ]
    model_instances = {
        "PeakData": {
            "model": "PeakData",
            "path": "",
            "reverse_path": "",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Peak Data Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    # "handoff": "",
                    # Using in link will expose the internal index field in the search form because there's no
                    # searchable unique field for handoff
                    "type": "number",
                },
                "labeled_element": {
                    "displayname": "Labeled Element",
                    "searchable": True,
                    "displayed": True,
                    "type": "enumeration",
                    "choices": TracerLabeledClass.TRACER_LABELED_ELEMENT_CHOICES,
                },
                "labeled_count": {
                    "displayname": "Labeled Count",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
                "raw_abundance": {
                    "displayname": "Raw Abundance",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
                "corrected_abundance": {
                    "displayname": "Corrected Abundance",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
                "fraction": {
                    "displayname": "Fraction",
                    "searchable": False,  # Cannot search cached property
                    "displayed": True,
                    "type": "number",
                },
                "med_mz": {
                    "displayname": "Median M/Z",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
                "med_rt": {
                    "displayname": "Median RT",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
            },
        },
        "PeakGroup": {
            "model": "PeakGroup",
            "path": "peak_group",
            "reverse_path": "peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Peak Group Index",  # Used in link
                    "searchable": True,
                    "displayed": False,
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Peak Group",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
                "formula": {
                    "displayname": "Formula",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "MeasuredCompound": {
            "model": "Compound",
            "path": "peak_group__compounds",
            "reverse_path": "peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Measured Compound Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Measured Compound (Primary Synonym)",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "CompoundSynonym": {
            "model": "CompoundSynonym",
            "path": "peak_group__compounds__synonyms",
            "reverse_path": "compound__peak_groups__peak_data",
            "manytomany": {
                "is": True,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Compound Synonym Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Measured Compound (Any Synonym)",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "PeakGroupSet": {
            "model": "PeakGroupSet",
            "path": "peak_group__peak_group_set",
            "reverse_path": "peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Peak Group Set Index",  # Used in link
                    "searchable": True,
                    "displayed": False,
                    "handoff": "filename",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "filename": {
                    "displayname": "Peak Group Set Filename",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "Sample": {
            "model": "Sample",
            "path": "peak_group__msrun__sample",
            "reverse_path": "msruns__peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Sample Index",  # Used in link
                    "searchable": True,
                    "displayed": False,
                    "type": "number",
                    "handoff": "name",
                },
                "name": {
                    "displayname": "Sample",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "Tissue": {
            "model": "Tissue",
            "path": "peak_group__msrun__sample__tissue",
            "reverse_path": "samples__msruns__peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "Tissue",
                    "searchable": True,
                    "displayed": False,
                    "type": "number",
                    "handoff": "name",
                },
                "name": {
                    "displayname": "Tissue",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "Animal": {
            "model": "Animal",
            "path": "peak_group__msrun__sample__animal",
            "reverse_path": "samples__msruns__peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Animal Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Animal",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
                "body_weight": {
                    "displayname": "Body Weight (g)",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
                "genotype": {
                    "displayname": "Genotype",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
                "sex": {
                    "displayname": "Sex",
                    "searchable": True,
                    "displayed": True,
                    "type": "enumeration",
                    "choices": Animal.SEX_CHOICES,
                },
                "age": {
                    "displayname": "Age (d-hh:mm:ss)",
                    "searchable": False,
                    "displayed": True,
                    "type": "number",
                },
                "feeding_status": {
                    "displayname": "Feeding Status",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
                "diet": {
                    "displayname": "Diet",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
                "tracer_infusion_concentration": {
                    "displayname": "Tracer Infusion Concentration (mM)",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
                "tracer_infusion_rate": {
                    "displayname": "Tracer Infusion Rate (ul/min/g)",
                    "searchable": True,
                    "displayed": True,
                    "type": "number",
                },
            },
        },
        "Protocol": {
            "model": "Protocol",
            "path": "peak_group__msrun__sample__animal__treatment",
            "reverse_path": "animals__samples__msruns__peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Protocol Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Treatment",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "TracerCompound": {
            "model": "Compound",
            "path": "peak_group__msrun__sample__animal__tracer_compound",
            "reverse_path": "animals__samples__msruns__peak_groups__peak_data",
            "manytomany": {
                "is": False,
                "split_rows": False,
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Tracer Compound Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Tracer Compound (Primary Synonym)",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
        "Study": {
            "model": "Study",
            "path": "peak_group__msrun__sample__animal__studies",
            "reverse_path": "animals__samples__msruns__peak_groups__peak_data",
            "manytomany": {
                "is": True,
                "split_rows": False,
                "root_annot_fld": "study",
            },
            "fields": {
                "id": {
                    "displayname": "(Internal) Study Index",
                    "searchable": True,
                    "displayed": False,  # Used in link
                    "handoff": "name",  # This is the field that will be loaded in the search form
                    "type": "number",
                },
                "name": {
                    "displayname": "Study",
                    "searchable": True,
                    "displayed": True,
                    "type": "string",
                },
            },
        },
    }
