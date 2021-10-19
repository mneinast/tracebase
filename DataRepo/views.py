import json
from datetime import datetime
from typing import List

from django.conf import settings
from django.core.management import call_command
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.test import TestCase
from django.test.utils import setup_databases, setup_test_environment
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormView

from DataRepo.compositeviews import BaseAdvancedSearchView
from DataRepo.forms import (
    AdvSearchDownloadForm,
    AdvSearchForm,
    DataSubmissionValidationForm,
)
from DataRepo.models import (
    Animal,
    Compound,
    MSRun,
    PeakData,
    PeakGroup,
    PeakGroupSet,
    Protocol,
    Sample,
    Study,
)
from DataRepo.multiforms import MultiFormsView
from DataRepo.utils import MissingSamplesError, ResearcherError


def home(request):
    return render(request, "home.html")


def upload(request):
    context = {
        "data_submission_email": settings.DATA_SUBMISSION_EMAIL,
        "data_submission_url": settings.DATA_SUBMISSION_URL,
    }
    return render(request, "upload.html", context)


class CompoundListView(ListView):
    """Generic class-based view for a list of compounds"""

    model = Compound
    context_object_name = "compound_list"
    template_name = "DataRepo/compound_list.html"
    ordering = ["name"]
    paginate_by = 20


class CompoundDetailView(DetailView):
    """Generic class-based detail view for a compound"""

    model = Compound
    template_name = "DataRepo/compound_detail.html"


class StudyListView(ListView):
    """Generic class-based view for a list of studies."""

    model = Study
    context_object_name = "study_list"
    template_name = "DataRepo/study_list.html"
    ordering = ["name"]
    paginate_by = 20


class StudyDetailView(DetailView):
    """Generic class-based detail view for a study."""

    model = Study
    template_name = "DataRepo/study_detail.html"


def search_basic(request, mdl, fld, cmp, val, fmt):
    """Generic function-based view for a basic search."""

    # Base Advanced Search View Metadata
    basv_metadata = BaseAdvancedSearchView()

    # Base Advanced Search Form
    basf = AdvSearchForm()

    format_template = "DataRepo/search/query.html"
    fmtkey = basv_metadata.formatNameOrKeyToKey(fmt)
    if fmtkey is None:
        names = basv_metadata.getFormatNames()
        raise Http404(
            f"Invalid format [{fmt}].  Must be one of: [{','.join(names.keys())},{','.join(names.values())}]"
        )

    qry = createNewBasicQuery(basv_metadata, mdl, fld, cmp, val, fmtkey)
    download_form = AdvSearchDownloadForm(initial={"qryjson": json.dumps(qry)})
    q_exp = constructAdvancedQuery(qry)
    res = performQuery(q_exp, fmtkey, basv_metadata)
    root_group = basv_metadata.getRootGroup()

    return render(
        request,
        format_template,
        {
            "forms": basf.form_classes,
            "qry": qry,
            "res": res,
            "download_form": download_form,
            "debug": settings.DEBUG,
            "root_group": root_group,
            "mode": "search",
            "default_format": basv_metadata.default_format,
        },
    )


# Based on:
#   https://stackoverflow.com/questions/15497693/django-can-class-based-views-accept-two-forms-at-a-time
class AdvancedSearchView(MultiFormsView):
    """
    This is the view for the advanced search page.
    """

    # Base Advanced Search View
    basv_metadata = BaseAdvancedSearchView()

    # Base Advanced Search Form
    basf = AdvSearchForm()

    # Advanced search download form
    download_form = AdvSearchDownloadForm()

    # MultiFormView class vars
    template_name = "DataRepo/search/query.html"
    form_classes = basf.form_classes
    success_url = ""
    mixedform_selected_formtype = basf.format_select_list_name
    mixedform_prefix_field = basf.hierarchy_path_field_name

    # Override get_context_data to retrieve mode from the query string
    def get_context_data(self, **kwargs):
        """
        Retrieves page context data.
        """

        context = super().get_context_data(**kwargs)

        # Optional url parameter should now be in self, so add it to the context
        mode = self.request.GET.get("mode", self.basv_metadata.default_mode)
        format = self.request.GET.get("format", self.basv_metadata.default_format)
        if mode not in self.basv_metadata.modes:
            mode = self.basv_metadata.default_mode
            # Log a warning
            print("WARNING: Invalid mode: ", mode)

        context["mode"] = mode
        context["format"] = format
        context["default_format"] = self.basv_metadata.default_format
        self.addInitialContext(context)

        return context

    def form_invalid(self, formset):
        """
        Upon invalid advanced search form submission, rescues the query to add back to the context.
        """

        qry = formsetsToDict(formset, self.form_classes)

        root_group = self.basv_metadata.getRootGroup()

        return self.render_to_response(
            self.get_context_data(
                res={},
                forms=self.form_classes,
                qry=qry,
                debug=settings.DEBUG,
                root_group=root_group,
                default_format=self.basv_metadata.default_format,
                ncmp_choices=self.basv_metadata.getComparisonChoices(),
                fld_types=self.basv_metadata.getFieldTypes(),
            )
        )

    def form_valid(self, formset):
        """
        Upon valid advanced search form submission, adds results (& query) to the context of the search page.
        """

        qry = formsetsToDict(formset, self.form_classes)
        res = {}
        download_form = {}

        if isQryObjValid(qry, self.form_classes.keys()):
            download_form = AdvSearchDownloadForm(initial={"qryjson": json.dumps(qry)})
            q_exp = constructAdvancedQuery(qry)
            performQuery(q_exp, qry["selectedtemplate"], self.basv_metadata)
        else:
            # Log a warning
            print("WARNING: Invalid query root:", qry)

        root_group = self.basv_metadata.getRootGroup()

        return self.render_to_response(
            self.get_context_data(
                res=res,
                forms=self.form_classes,
                qry=qry,
                download_form=download_form,
                debug=settings.DEBUG,
                root_group=root_group,
                default_format=self.basv_metadata.default_format,
                ncmp_choices=self.basv_metadata.getComparisonChoices(),
                fld_types=self.basv_metadata.getFieldTypes(),
            )
        )

    def addInitialContext(self, context):
        """
        Prepares context data for the initial page load.
        """

        mode = self.basv_metadata.default_mode
        if "mode" in context and context["mode"] == "browse":
            mode = "browse"
        context["mode"] = mode

        context["root_group"] = self.basv_metadata.getRootGroup()
        context["ncmp_choices"] = self.basv_metadata.getComparisonChoices()
        context["fld_types"] = self.basv_metadata.getFieldTypes()

        if "qry" not in context or (
            mode == "browse" and not isValidQryObjPopulated(context["qry"])
        ):
            if "qry" not in context:
                if "format" in context:
                    qry = self.basv_metadata.getRootGroup(context["format"])
                else:
                    qry = self.basv_metadata.getRootGroup()
            else:
                qry = context["qry"]

            if mode == "browse":
                context["download_form"] = AdvSearchDownloadForm(
                    initial={"qryjson": json.dumps(qry)}
                )
                context["res"] = getAllBrowseData(
                    qry["selectedtemplate"], self.basv_metadata
                )

        elif (
            "qry" in context
            and isValidQryObjPopulated(context["qry"])
            and ("res" not in context or len(context["res"]) == 0)
        ):
            qry = context["qry"]
            context["download_form"] = AdvSearchDownloadForm(
                initial={"qryjson": json.dumps(qry)}
            )
            q_exp = constructAdvancedQuery(qry)
            context["res"] = performQuery(
                q_exp, qry["selectedtemplate"], self.basv_metadata
            )


# Basis: https://stackoverflow.com/questions/29672477/django-export-current-queryset-to-csv-by-button-click-in-browser
class AdvancedSearchTSVView(FormView):
    """
    This is the download view for the advanced search page.
    """

    form_class = AdvSearchDownloadForm
    template_name = "DataRepo/search/downloads/download.tsv"
    content_type = "application/text"
    success_url = ""
    basv_metadata = BaseAdvancedSearchView()

    def form_invalid(self, form):
        saved_form = form.saved_data
        qry = {}
        if "qryjson" in saved_form:
            # Discovered this can cause a KeyError during testing, so...
            qry = json.loads(saved_form["qryjson"])
        else:
            print("ERROR: qryjson hidden input not in saved form.")
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        res = {}
        return self.render_to_response(
            self.get_context_data(res=res, qry=qry, dt=dt_string, debug=settings.DEBUG)
        )

    def form_valid(self, form):
        cform = form.cleaned_data
        try:
            qry = json.loads(cform["qryjson"])
            # Apparently this causes a TypeError exception in test_views. Could not figure out why, so...
        except TypeError:
            qry = cform["qryjson"]
        if not isQryObjValid(qry, self.basv_metadata.getFormatNames().keys()):
            print("Invalid qry object: ", qry)
            raise Http404("Invalid json")

        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        filename = (
            qry["searches"][qry["selectedtemplate"]]["name"]
            + "_"
            + now.strftime("%d.%m.%Y.%H.%M.%S")
            + ".tsv"
        )

        if isValidQryObjPopulated(qry):
            q_exp = constructAdvancedQuery(qry)
            res = performQuery(q_exp, qry["selectedtemplate"], self.basv_metadata)
        else:
            res = getAllBrowseData(qry["selectedtemplate"], self.basv_metadata)

        response = self.render_to_response(
            self.get_context_data(res=res, qry=qry, dt=dt_string, debug=settings.DEBUG)
        )
        response["Content-Disposition"] = "attachment; filename={}".format(filename)

        return response


def getAllBrowseData(format, basv):
    """
    Grabs all data without a filtering match for browsing.
    """

    if format in basv.getFormatNames().keys():
        res = basv.modeldata[format].rootqs.all()
    else:
        # Log a warning
        print("WARNING: Unknown format: " + format)
        return {}

    prefetches = basv.getPrefetches(format)
    if prefetches is not None:
        res2 = res.prefetch_related(*prefetches)
    else:
        res2 = res

    return res2


def createNewAdvancedQuery(basv_metadata, context):
    """
    Constructs an empty qry for the advanced search interface.
    """

    if "format" in context:
        qry = basv_metadata.getRootGroup(context["format"])
    else:
        qry = basv_metadata.getRootGroup()

    return qry


def createNewBasicQuery(basv_metadata, mdl, fld, cmp, val, fmt):
    """
    Constructs a new qry object for an advanced search from basic search input.
    """

    qry = basv_metadata.getRootGroup(fmt)

    models = basv_metadata.getModels(fmt)

    if mdl not in models:
        raise Http404(
            "Invalid model [" + mdl + "].  Must be one of [" + ",".join(models) + "]."
        )

    sfields = basv_metadata.getSearchFields(fmt, mdl)

    if fld not in sfields:
        raise Http404(
            f"Field [{fld}] is not searchable.  Must be one of [{','.join(sfields.keys())}]."
        )

    qry["searches"][fmt]["tree"]["queryGroup"].append({})
    qry["searches"][fmt]["tree"]["queryGroup"][0]["type"] = "query"
    qry["searches"][fmt]["tree"]["queryGroup"][0]["pos"] = ""
    qry["searches"][fmt]["tree"]["queryGroup"][0]["fld"] = sfields[fld]
    qry["searches"][fmt]["tree"]["queryGroup"][0]["ncmp"] = cmp
    qry["searches"][fmt]["tree"]["queryGroup"][0]["val"] = val

    dfld, dval = searchFieldToDisplayField(basv_metadata, mdl, fld, val, fmt, qry)
    # Set the field path for the display field
    qry["searches"][fmt]["tree"]["queryGroup"][0]["fld"] = sfields[dfld]
    qry["searches"][fmt]["tree"]["queryGroup"][0]["val"] = dval

    return qry


def searchFieldToDisplayField(basv_metadata, mdl, fld, val, fmt, qry):
    """
    Takes a field from a basic search and converts it to a non-hidden field for an advanced search select list.
    """

    dfld = fld
    dval = val
    dfields = basv_metadata.getDisplayFields(fmt, mdl)
    if fld in dfields.keys() and dfields[fld] != fld:
        # If fld is not a displayed field, perform a query to convert the undisplayed field query to a displayed query
        q_exp = constructAdvancedQuery(qry)
        recs = performQuery(q_exp, fmt, basv_metadata)
        if len(recs) == 0:
            raise Http404("Records not found for field [" + mdl + "." + fld + "].")
        # Set the field path for the display field
        dfld = dfields[fld]
        dval = getJoinedRecFieldValue(recs, basv_metadata, fmt, mdl, dfields[fld])

    return dfld, dval


def getJoinedRecFieldValue(recs, basv_metadata, fmt, mdl, fld):
    """
    Takes a queryset object and a model.field and returns its value.
    """

    if len(recs) == 0:
        raise Http404("Records not found.")

    kpl = basv_metadata.getKeyPathList(fmt, mdl)
    kpl.append(fld)
    ptr = recs[0]
    for key in kpl:
        # If this is a many-to-many
        if ptr.__class__.__name__ == "ManyRelatedManager":
            tmprecs = ptr.all()
            if len(tmprecs) != 1:
                # Log an error
                print(
                    f"ERROR: Handoff to {mdl}.{fld} failed.  Too many records returned.  Expected 1.  Check the "
                    "AdvSearch class handoffs."
                )
                raise Http404(f"ERROR: Unable to find a single value for [{mdl}.{fld}].")
            ptr = getattr(tmprecs[0], key)
        else:
            ptr = getattr(ptr, key)

    return ptr


def performQuery(q_exp, fmt, basv):
    """
    Executes an advanced search query.
    """

    res = {}
    if fmt in basv.getFormatNames().keys():
        res = basv.modeldata[fmt].rootqs.filter(q_exp)
    else:
        # Log a warning
        print("WARNING: Invalid selected format:", fmt)

    prefetches = basv.getPrefetches(fmt)
    if prefetches is not None:
        res2 = res.prefetch_related(*prefetches)
    else:
        res2 = res

    return res2


def isQryObjValid(qry, form_class_list):
    """
    Determines if an advanced search qry object was properly constructed/populated (only at the root).
    """

    if (
        type(qry) is dict
        and "selectedtemplate" in qry
        and "searches" in qry
        and len(form_class_list) == len(qry["searches"].keys())
    ):
        for key in form_class_list:
            if (
                key not in qry["searches"]
                or type(qry["searches"][key]) is not dict
                or "tree" not in qry["searches"][key]
                or "name" not in qry["searches"][key]
            ):
                print("qry is either missing keys 'tree' and/or 'name', or searches is not a dict")
                return False
        return True
    else:
        print("qry is either missing keys 'selectedtemplate', 'searches', or one of the template keys in searches")
        return False


def isValidQryObjPopulated(qry):
    """
    Checks whether a query object is fully populated with at least 1 search term.
    """
    selfmt = qry["selectedtemplate"]
    if len(qry["searches"][selfmt]["tree"]["queryGroup"]) == 0:
        return False
    else:
        return isValidQryObjPopulatedHelper(qry["searches"][selfmt]["tree"]["queryGroup"])


def isValidQryObjPopulatedHelper(group):
    for query in group:
        if query["type"] == "query":
            if not query["val"] or query["val"] == "":
                return False
        elif query["type"] == "group":
            if len(group["queryGroup"]) == 0:
                return False
            else:
                tmp_populated = isValidQryObjPopulatedHelper(group["queryGroup"])
                if not tmp_populated:
                    return False
    return True



def constructAdvancedQuery(qryRoot):
    """
    Turns a qry object into a complex Q object by calling its helper and supplying the selected format's tree.
    """

    return constructAdvancedQueryHelper(
        qryRoot["searches"][qryRoot["selectedtemplate"]]["tree"]
    )


def constructAdvancedQueryHelper(qry):
    """
    Recursively build a complex Q object based on a hierarchical tree defining the search terms.
    """

    if qry["type"] == "query":
        cmp = qry["ncmp"].replace("not_", "", 1)
        negate = cmp != qry["ncmp"]

        # Special case for isnull (ignores qry['val'])
        if cmp == "isnull":
            if negate:
                negate = False
                qry["val"] = False
            else:
                qry["val"] = True

        criteria = {"{0}__{1}".format(qry["fld"], cmp): qry["val"]}
        if negate is False:
            return Q(**criteria)
        else:
            return ~Q(**criteria)

    elif qry["type"] == "group":
        q = Q()
        gotone = False
        for elem in qry["queryGroup"]:
            gotone = True
            if qry["val"] == "all":
                nq = constructAdvancedQueryHelper(elem)
                if nq is None:
                    return None
                else:
                    q &= nq
            elif qry["val"] == "any":
                nq = constructAdvancedQueryHelper(elem)
                if nq is None:
                    return None
                else:
                    q |= nq
            else:
                return None
        if not gotone or q is None:
            return None
        else:
            return q
    return None


def formsetsToDict(rawformset, form_classes):
    """
    Takes a series of forms and a list of form fields and uses the pos field to construct a hierarchical qry tree.
    """

    # All forms of each type are all submitted together in a single submission and are duplicated in the rawformset
    # dict.  We only need 1 copy to get all the data, so we will arbitrarily use the first one

    # Figure out which form class processed the forms (inferred by the presence of 'saved_data' - this is also the
    # selected format)
    processed_formkey = None
    for key in rawformset.keys():
        # We need to identify the form class that processed the form to infer the selected output format.  We do that
        # by checking the dictionary of each form class's first form for evidence that it processed the forms, i.e. the
        # presence of the "saved_data" class data member which is created upon processing.
        if "saved_data" in rawformset[key][0].__dict__:
            processed_formkey = key
            break

    # If we were unable to locate the selected output format (i.e. the copy of the formsets that were processed)
    if processed_formkey is None:
        raise Http404(f"Unable to find the saved form-processed data among formats: {','.join(rawformset.keys())}.")

    return formsetToDict(rawformset[processed_formkey], form_classes)


def formsetToDict(rawformset, form_classes):
    """
    Helper for formsetsToDict that handles only the forms belonging to the selected output format.
    """

    search = {"selectedtemplate": "", "searches": {}}

    # We take a raw form instead of cleaned_data so that form_invalid will repopulate the bad form as-is
    isRaw = False
    try:
        formset = rawformset.cleaned_data
    except AttributeError:
        isRaw = True
        formset = rawformset

    for rawform in formset:

        if isRaw:
            form = rawform.saved_data
        else:
            form = rawform

        path = form["pos"].split(".")

        [format, formatName, selected] = rootToFormatInfo(path.pop(0))
        rootinfo = path.pop(0)

        # If this format has not yet been initialized
        if format not in search["searches"]:
            search["searches"][format] = {}
            search["searches"][format]["tree"] = {}
            search["searches"][format]["name"] = formatName

            # Initialize the root of the tree
            [pos, gtype, static] = pathStepToPosGroupType(rootinfo)
            aroot = search["searches"][format]["tree"]
            aroot["pos"] = ""
            aroot["type"] = "group"
            aroot["val"] = gtype
            aroot["static"] = static
            aroot["queryGroup"] = []
            curqry = aroot["queryGroup"]
        else:
            # The root already exists, so go directly to its child list
            curqry = search["searches"][format]["tree"]["queryGroup"]

        if selected is True:
            search["selectedtemplate"] = format

        for spot in path:
            [pos, gtype, static] = pathStepToPosGroupType(spot)
            while len(curqry) <= pos:
                curqry.append({})
            if gtype is not None:
                # This is a group
                # If the inner node was not already set
                if not curqry[pos]:
                    curqry[pos]["pos"] = ""
                    curqry[pos]["type"] = "group"
                    curqry[pos]["val"] = gtype
                    curqry[pos]["static"] = static
                    curqry[pos]["queryGroup"] = []
                # Move on to the next node in the path
                curqry = curqry[pos]["queryGroup"]
            else:
                # This is a query

                # Keep track of keys encountered
                keys_seen = {}
                for key in form_classes[format].form.base_fields.keys():
                    keys_seen[key] = 0
                cmpnts = []

                curqry[pos]["type"] = "query"

                # Set the form values in the query based on the form elements
                for key in form.keys():
                    # Remove "form-#-" from the form element ID
                    cmpnts = key.split("-")
                    keyname = cmpnts[-1]
                    keys_seen[key] = 1
                    if keyname == "pos":
                        curqry[pos][key] = ""
                    elif keyname == "static":
                        if form[key] == "true":
                            curqry[pos][key] = True
                        else:
                            curqry[pos][key] = False
                    elif key not in curqry[pos]:
                        curqry[pos][key] = form[key]
                    else:
                        # Log a warning
                        print(f"WARNING: Unrecognized form element not set at pos {pos}: {key} to {form[key]}")

                # Now initialize anything missing a value to an empty string
                # This is used to correctly reconstruct the user's query upon form_invalid
                for key in form_classes[format].form.base_fields.keys():
                    if keys_seen[key] == 0:
                        curqry[pos][key] = ""
    return search


def pathStepToPosGroupType(spot):
    """
    Takes a substring from a pos field defining a single tree node and returns its position and group type (if it's an
    inner node).  E.g. "0-all"
    """

    pos_gtype_stc = spot.split("-")
    if len(pos_gtype_stc) == 3:
        pos = pos_gtype_stc[0]
        gtype = pos_gtype_stc[1]
        if pos_gtype_stc[2] == 'true':
            static = True
        else:
            static = False
    elif len(pos_gtype_stc) == 2:
        pos = pos_gtype_stc[0]
        gtype = pos_gtype_stc[1]
        static = False
    else:
        pos = spot
        gtype = None
        static = False
    pos = int(pos)
    return [pos, gtype, static]


def rootToFormatInfo(rootInfo):
    """
    Takes the first substring from a pos field defining the root node and returns the format code, format name, and
    whether it is the selected format.
    """

    val_name_sel = rootInfo.split("-")
    sel = False
    name = ""
    if len(val_name_sel) == 3:
        val = val_name_sel[0]
        name = val_name_sel[1]
        if val_name_sel[2] == "selected":
            sel = True
    elif len(val_name_sel) == 2:
        val = val_name_sel[0]
        name = val_name_sel[1]
    else:
        print("WARNING: Unable to parse format name from submitted form data.")
        val = val_name_sel
        name = val_name_sel
    return [val, name, sel]


class ProtocolListView(ListView):
    """Generic class-based view for a list of protocols"""

    model = Protocol
    context_object_name = "protocol_list"
    template_name = "DataRepo/protocol_list.html"
    ordering = ["name"]
    paginate_by = 20


class ProtocolDetailView(DetailView):
    """Generic class-based detail view for a protocol"""

    model = Protocol
    template_name = "DataRepo/protocol_detail.html"


class AnimalListView(ListView):
    """Generic class-based view for a list of animals"""

    model = Animal
    context_object_name = "animal_list"
    template_name = "DataRepo/animal_list.html"
    ordering = ["name"]
    paginate_by = 20


class AnimalDetailView(DetailView):
    """Generic class-based detail view for an animal"""

    model = Animal
    template_name = "DataRepo/animal_detail.html"


class SampleListView(ListView):
    """
    Generic class-based view for a list of samples
    "model = Sample" is shorthand for queryset = Sample.objects.all()
    use queryset syntax for sample list with or without filtering
    """

    # return all samples without query filter
    queryset = Sample.objects.all()
    context_object_name = "sample_list"
    template_name = "DataRepo/sample_list.html"
    ordering = ["animal_id", "name"]
    paginate_by = 20

    # filter sample list by animal_id
    def get_queryset(self):
        queryset = super().get_queryset()
        # get query string from request
        animal_pk = self.request.GET.get("animal_id", None)
        if animal_pk is not None:
            self.animal = get_object_or_404(Animal, id=animal_pk)
            queryset = Sample.objects.filter(animal_id=animal_pk)
        return queryset


class SampleDetailView(DetailView):
    """Generic class-based detail view for a sample"""

    model = Sample
    template_name = "DataRepo/sample_detail.html"


class MSRunListView(ListView):
    """Generic class-based view for a list of MS runs"""

    model = MSRun
    context_object_name = "msrun_list"
    template_name = "DataRepo/msrun_list.html"
    ordering = ["id"]
    paginate_by = 20


class MSRunDetailView(DetailView):
    """Generic class-based detail view for a MS run"""

    model = MSRun
    template_name = "DataRepo/msrun_detail.html"


class PeakGroupSetListView(ListView):
    """Generic class-based view for a list of PeakGroup sets"""

    model = PeakGroupSet
    context_object_name = "peakgroupset_list"
    template_name = "DataRepo/peakgroupset_list.html"
    ordering = ["id"]
    paginate_by = 20


class PeakGroupSetDetailView(DetailView):
    """Generic class-based detail view for a PeakGroup set"""

    model = PeakGroupSet
    template_name = "DataRepo/peakgroupset_detail.html"


class PeakGroupListView(ListView):
    """
    Generic class-based view for a list of peak groups
    "model = PeakGroup" is shorthand for queryset = PeakGroup.objects.all()
    use queryset syntax for PeakGroup list with or without filtering
    """

    queryset = PeakGroup.objects.all()
    context_object_name = "peakgroup_list"
    template_name = "DataRepo/peakgroup_list.html"
    ordering = ["msrun_id", "peak_group_set_id", "name"]
    paginate_by = 50

    # filter the peakgroup_list by msrun_id
    def get_queryset(self):
        queryset = super().get_queryset()
        # get query string from request
        msrun_pk = self.request.GET.get("msrun_id", None)
        if msrun_pk is not None:
            self.msrun = get_object_or_404(MSRun, id=msrun_pk)
            queryset = PeakGroup.objects.filter(msrun_id=msrun_pk)
        return queryset


class PeakGroupDetailView(DetailView):
    """Generic class-based detail view for a peak group"""

    model = PeakGroup
    template_name = "DataRepo/peakgroup_detail.html"


class PeakDataListView(ListView):
    """
    Generic class-based view for a list of peak data
    "model = PeakData" is shorthand for queryset = PeakData.objects.all()
    use queryset syntax for PeakData list with or without filtering
    """

    queryset = PeakData.objects.all()
    context_object_name = "peakdata_list"
    template_name = "DataRepo/peakdata_list.html"
    ordering = ["peak_group_id", "id"]
    paginate_by = 200

    # filter peakgdata_list by peak_group_id
    def get_queryset(self):
        queryset = super().get_queryset()
        # get query string from request
        peakgroup_pk = self.request.GET.get("peak_group_id", None)
        if peakgroup_pk is not None:
            self.peakgroup = get_object_or_404(PeakGroup, id=peakgroup_pk)
            queryset = PeakData.objects.filter(peak_group_id=peakgroup_pk)
        return queryset


class DataValidationView(FormView):
    form_class = DataSubmissionValidationForm
    template_name = "DataRepo/validate_submission.html"
    success_url = ""
    accucor_files: List[str] = []
    animal_sample_file = None
    submission_url = settings.DATA_SUBMISSION_URL

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        self.accucor_files = request.FILES.getlist("accucor_files")
        try:
            self.animal_sample_file = request.FILES["animal_sample_table"]
        except Exception:
            # Ignore missing accucor files
            print("No accucor file")
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """
        Upon valid file submission, adds validation messages to the context of the validation page.
        """

        errors = {}
        debug = "untouched"
        valid = True
        results = {}
        ash_yaml = "DataRepo/example_data/sample_and_animal_tables_headers.yaml"

        debug = f"asf: {self.animal_sample_file} num afs: {len(self.accucor_files)}"

        animal_sample_dict = {
            str(self.animal_sample_file): self.animal_sample_file.temporary_file_path(),
        }
        accucor_dict = dict(
            map(lambda x: (str(x), x.temporary_file_path()), self.accucor_files)
        )

        [results, valid, errors] = self.validate_load_files(
            animal_sample_dict, accucor_dict, ash_yaml
        )

        return self.render_to_response(
            self.get_context_data(
                results=results,
                debug=debug,
                valid=valid,
                form=form,
                errors=errors,
                submission_url=self.submission_url,
            )
        )

    def validate_load_files(self, animal_sample_dict, accucor_dict, ash_yaml):
        errors = {}
        valid = True
        results = {}
        animal_sample_name = list(animal_sample_dict.keys())[0]

        # Load the animal and sample table in debug mode to check the researcher and sample name uniqueness
        errors[animal_sample_name] = []
        results[animal_sample_name] = ""
        try:
            call_command(
                "load_animals_and_samples",
                animal_and_sample_table_filename=animal_sample_dict[animal_sample_name],
                table_headers=ash_yaml,
                debug=True,
            )
            results[animal_sample_name] = "PASSED"
        except ResearcherError as re:
            valid = False
            errors[animal_sample_name].append(
                "[The following error about a new researcher name should only be addressed if the name already exists "
                "in the database as a variation.  If this is a truly new researcher name in the database, it may be "
                f"ignored.]\n{animal_sample_name}: {str(re)}"
            )
            results[animal_sample_name] = "WARNING"
        except Exception as e:
            valid = False
            errors[animal_sample_name].append(f"{animal_sample_name}: {str(e)}")
            results[animal_sample_name] = "FAILED"

        can_proceed = False
        if results[animal_sample_name] != "FAILED":
            # Load the animal and sample data into a test database, so the data is available for the accucor file
            # validation
            validation_test = self.ValidationTest()
            try:
                validation_test.validate_animal_sample_table(
                    animal_sample_dict[animal_sample_name],
                    ash_yaml,
                )
                can_proceed = True
            except Exception as e:
                errors[animal_sample_name].append(f"{animal_sample_name}: {str(e)}")
                can_proceed = False

        # Load the accucor file into a temporary test database in debug mode
        for af, afp in accucor_dict.items():
            errors[af] = []
            if can_proceed is True:
                try:
                    validation_test.validate_accucor(
                        afp,
                        [],
                    )
                    results[af] = "PASSED"
                except MissingSamplesError as mse:
                    blank_samples = []
                    real_samples = []

                    # Determine whether all the missing samples are blank samples
                    for sample in mse.sample_list:
                        if "blank" in sample:
                            blank_samples.append(sample)
                        else:
                            real_samples.append(sample)

                    # Rerun ignoring blanks if all were blank samples, so we can check everything else
                    if len(blank_samples) > 0 and len(blank_samples) == len(
                        mse.sample_list
                    ):
                        try:
                            validation_test.validate_accucor(
                                afp,
                                blank_samples,
                            )
                            results[af] = "PASSED"
                        except Exception as e:
                            estr = str(e)
                            if "Debugging" not in estr:
                                valid = False
                                results[af] = "FAILED"
                                errors[af].append(estr)
                            else:
                                results[af] = "PASSED"
                    else:
                        valid = False
                        results[af] = "FAILED"
                        errors[af].append(
                            "Samples in the accucor file are missing in the animal and sample table: "
                            ", ".join(real_samples)
                        )
                except Exception as e:
                    estr = str(e)
                    if "Debugging" not in estr:
                        valid = False
                        results[af] = "FAILED"
                        errors[af].append(estr)
                    else:
                        results[af] = "PASSED"
            else:
                # Cannot check because the samples did not load
                results[af] = "UNCHECKED"
        return [
            results,
            valid,
            errors,
        ]

    class ValidationTest(TestCase):
        @classmethod
        def setUpTestData(cls):
            setup_databases(keepdb=False)
            setup_test_environment()
            call_command("load_compounds", "DataRepo/example_data/obob_compounds.tsv")

        def validate_animal_sample_table(self, animal_sample_file, table_headers):
            call_command(
                "load_animals_and_samples",
                animal_and_sample_table_filename=animal_sample_file,
                table_headers=table_headers,
                skip_researcher_check=True,
            )

        def validate_accucor(self, accucor_file, skip_samples):
            if len(skip_samples) > 0:
                call_command(
                    "load_accucor_msruns",
                    protocol="Default",
                    accucor_file=accucor_file,
                    date="2021-09-14",
                    researcher="Michael Neinast",
                    debug=True,
                    skip_samples=skip_samples,
                )
            else:
                call_command(
                    "load_accucor_msruns",
                    protocol="Default",
                    accucor_file=accucor_file,
                    date="2021-09-13",
                    researcher="Michael Neinast",
                    debug=True,
                )
