from django.core.exceptions import FieldError, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormView
from django.db.models import Q
from django.forms import formset_factory
import json

from DataRepo.forms import AdvSearchPeakGroupsForm

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
#    TracerLabeledClass,
)


def home(request):
    return render(request, "home.html")


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

    qry = {}
    qry["mdl"] = mdl
    qry["fld"] = fld
    qry["cmp"] = cmp
    qry["val"] = val
    qry["fmt"] = fmt

    format_template = ""
    if fmt == "peakgroups":
        format_template = "peakgroups_results.html"
        fld_cmp = ""

        if mdl == "Study":
            fld_cmp = "peak_group__ms_run__sample__animal__studies__"
        elif mdl == "Animal":
            fld_cmp = "peak_group__ms_run__sample__animal__"
        elif mdl == "Sample":
            fld_cmp = "peak_group__ms_run__sample__"
        elif mdl == "Tissue":
            fld_cmp = "peak_group__ms_run__sample__tissue__"
        elif mdl == "MSRun":
            fld_cmp = "peak_group__ms_run__"
        elif mdl == "PeakGroup":
            fld_cmp = "peak_group__"
        elif mdl != "PeakData":
            raise Http404(
                "Table [" + mdl + "] is not searchable in the [" + fmt + "] "
                "results format."
            )

        fld_cmp += fld + "__" + cmp

        try:
            peakdata = PeakData.objects.filter(**{fld_cmp: val}).prefetch_related(
                "peak_group__ms_run__sample__animal__studies"
            )
        except FieldError as fe:
            raise Http404(
                "Table ["
                + mdl
                + "] either does not contain a field named ["
                + fld
                + "] or that field is not searchable.  Note, none of "
                "the cached property fields are searchable.  The error was: ["
                + str(fe)
                + "]."
            )

        res = render(request, format_template, {"qry": qry, "pds": peakdata})
    else:
        raise Http404("Results format [" + fmt + "] page not found")

    return res


#def search_advanced_start(request):
#    text_cmps = [
#        {"show":"is","cmp":"iexact"},
#        {"show":"is not","cmp":"not_iexact"},
#        {"show":"starts with","cmp":"istartswith"},
#        {"show":"doesn't start with","cmp":"not_istartswith"},
#        {"show":"contains","cmp":"icontains"},
#        {"show":"doesn't contain","cmp":"not_icontains"},
#        {"show":"ends with","cmp":"iendswith"},
#        {"show":"doesn't end with","cmp":"not_iendswith"}
#    ]
#    searchables = {}
#    searchables["fmt"] = {}
#    searchables["fmt"]["peakgroups"] = {
#        "Compound": {
#            "entry_type": "textbox",
#            "comparators": text_cmps,
#            "field": "peak_group__name"
#        },
#        "Atom": {
#            "entry_type": "select",
#            "options": TracerLabeledClass.tracer_labeled_elements_list(),
#            "field": "labeled_element"
#        }
#    }
#    return render(request, "search_advanced.html", {"searchables": searchables})


class AdvSearchPeakGroupsFmtView(FormView):
    form_class = formset_factory(AdvSearchPeakGroupsForm)
    template_name = 'DataRepo/peakgroups_results2.html'
    success_url = ''

    def form_valid(self, form):
        print(form.cleaned_data)
        print(form)
        # Build the query chain
        criteria = []
        for form_query in form.cleaned_data:
            cmp = form_query['ncmp'].replace("not_", "", 1)
            q = {'{0}__{1}'.format(form_query['fld'], cmp): form_query['val']}
            if cmp == form_query['ncmp']:
                criteria.append(Q(**q))
            else:
                criteria.append(~Q(**q))

        # If there was no search criteria, show all records
        #if len(criteria) == 0:
            #res = PeakData.objects.all().prefetch_related(
            #    "peak_group__ms_run__sample__animal__studies"
            #)

            # The form factory works by cloning, thus for new formsets to be
            # created when no forms were submitted, we need to produce a new
            # form from the factory
            form = formset_factory(AdvSearchPeakGroupsForm)
        #else:
            #res = PeakData.objects.filter(*criteria).prefetch_related(
            #    "peak_group__ms_run__sample__animal__studies"
            #)
        res = {}

        return self.render_to_response(self.get_context_data(res=res, form=form))


class AdvSearchPeakGroupsFmtViewTMP(FormView):
    form_class = formset_factory(AdvSearchPeakGroupsForm)
    template_name = 'DataRepo/peakgroups_results3.html'
    success_url = ''

    def form_invalid(self, form):
        print("The form was invalid")
        print(form)
        qry = formsetToHash(form,AdvSearchPeakGroupsForm.base_fields.keys())
        res = {}
        return self.render_to_response(self.get_context_data(res=res, form=form, qry=qry))

    def form_valid(self, form):
        print("The form was valid")
        print(form.cleaned_data)
        qry = formsetToHash(form,AdvSearchPeakGroupsForm.base_fields.keys())
        print(json.dumps(qry, indent=4))
        res = {}
        return self.render_to_response(self.get_context_data(res=res, form=form, qry=qry))

def formsetToHash(rawformset, form_fields):
    qry = []

    isRaw = False
    try:
        formset = rawformset.cleaned_data
    except:
        isRaw = True
        formset = rawformset

    for rawform in formset:

        if isRaw:
            form = rawform.saved_data
        else:
            form = rawform

        curqry = qry
        path = form["pos"].split(".")
        for spot in path:
            pos_gtype = spot.split("-")
            if len(pos_gtype) == 2:
                pos = pos_gtype[0]
                gtype = pos_gtype[1]
            else:
                pos = spot
                gtype = None
            pos = int(pos)
            while len(curqry) <= pos:
                curqry.append({})
            if gtype is not None:
                if not curqry[pos]:
                    # This is a group
                    curqry[pos]["pos"] = ""
                    curqry[pos]["type"] = "group"
                    curqry[pos]["val"] = gtype
                    curqry[pos]["queryGroup"] = []
                curqry = curqry[pos]["queryGroup"]
                print("Setting pointer to",pos,"queryGroup")
            else:
                # This is a query
                print("Setting pos",pos,"type to query")

                # Keep track of keys encountered
                keys_seen = {}
                for key in form_fields:
                    keys_seen[key] = 0
                cmpnts = []

                curqry[pos]["type"] = "query"
                for key in form.keys():
                    cmpnts = key.split("-")
                    keyname = cmpnts[-1]
                    keys_seen[key] = 1
                    if keyname == "pos":
                        curqry[pos][key] = ""
                    elif key not in curqry[pos]:
                        print("Setting pos",pos,key,"to",form[key])
                        curqry[pos][key] = form[key]
                    else:
                        print("ERROR: NOT setting pos",pos,key,"to",form[key])

                # Now initialize anything missing a value to an empty string
                # This is to be able to correctly reconstruct the user's query upon form_invalid
                for key in form_fields:
                    if keys_seen[key] == 0:
                        curqry[pos][key] = ""

                print()
    return qry


# used by templatetags/advsrch_tags.py
def getAllPeakGroupsFmtData():
    return PeakData.objects.all().prefetch_related(
        "peak_group__ms_run__sample__animal__studies"
    )


class ProtocolListView(ListView):
    """Generic class-based view for aa list of protocols"""

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
    """Generic class-based view for aa list of animals"""

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
    ordering = ["ms_run_id", "peak_group_set_id", "name"]
    paginate_by = 50

    # filter the peakgroup_list by ms_run_id
    def get_queryset(self):
        queryset = super().get_queryset()
        # get query string from request
        msrun_pk = self.request.GET.get("ms_run_id", None)
        if msrun_pk is not None:
            self.msrun = get_object_or_404(MSRun, id=msrun_pk)
            queryset = PeakGroup.objects.filter(ms_run_id=msrun_pk)
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
