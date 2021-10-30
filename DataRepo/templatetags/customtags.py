from django import template
from django.template.defaultfilters import floatformat
from DataRepo.views import manyToManyFilter

register = template.Library()


@register.filter
def getFormatName(qry, fmt):
    """
    Retrieves a format name, given a format
    """
    return qry["searches"][fmt]["name"]


@register.filter
def durationToWeeks(td):
    if td is None:
        return None
    return td.total_seconds() // 604800


@register.filter
def durationToMins(td):
    if td is None:
        return None
    return td.total_seconds() // 60


@register.filter
def decimalPlaces(number, places):
    if number is None:
        return None
    return floatformat(number, places)


# This allows indexing a list or dict
@register.filter
def index(indexable, i):
    return indexable[i]


@register.simple_tag
def define(the_val):
    return the_val


@register.filter
def getClass(state):
    styleclass = None
    if state is None:
        styleclass = ""
    elif state == "FAILED":
        styleclass = "text-danger"
    elif state == "WARNING":
        styleclass = "text-warning"
    elif state == "PASSED":
        styleclass = "text-success"
    else:
        styleclass = "text-info"
    return styleclass


@register.filter
def count_tracer_groups(res):
    cnt = 0
    for pg in res.all():
        if pg.is_tracer_compound_group:
            cnt = cnt + 1
    return cnt


@register.filter
def joinStudyNames(delimiter, recs):
    return delimiter.join(
        list(map(lambda studyrec: studyrec["name"], recs.values("name")))
    )

@register.simple_tag
def queryFilter(rootrec, mm_keypath, mm_rec, qry):
    print("Sending match result: ", manyToManyFilter(rootrec, mm_keypath, mm_rec, qry))
    return manyToManyFilter(rootrec, mm_keypath, mm_rec, qry)
