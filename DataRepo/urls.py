from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("upload", views.upload, name="upload"),
    path("validate", views.DataValidationView.as_view(), name="validate"),
    path("validatedown", views.validation_disabled, name="validatedown"),
    path(
        "search_basic/<str:mdl>/<str:fld>/<str:cmp>/<str:val>/<str:fmt>/",
        views.search_basic,
        name="search_basic",
    ),
    path(
        "static_search_results/",
        views.view_search_results,
        name="view_search_results",
    ),
    path(
        "search_advanced/",
        views.AdvancedSearchView.as_view(),
        name="search_advanced",
    ),
    path(
        "search_advanced_tsv/",
        views.AdvancedSearchTSVView.as_view(),
        name="search_advanced_tsv",
    ),
    path("compounds/", views.CompoundListView.as_view(), name="compound_list"),
    path(
        "compounds/<int:pk>/",
        views.CompoundDetailView.as_view(),
        name="compound_detail",
    ),
    path("studies/", views.StudyListView.as_view(), name="study_list"),
    path("studies/<int:pk>/", views.StudyDetailView.as_view(), name="study_detail"),
    path("studies/study_summary/", views.study_summary, name="study_summary"),
    path(
        "protocols/animal_treatments/",
        views.AnimalTreatmentListView.as_view(),
        name="animal_treatment_list",
    ),
    path(
        "protocols/msrun_protocols/",
        views.MSRunProtocolListView.as_view(),
        name="msrun_protocol_list",
    ),
    path(
        "protocols/<int:pk>/",
        views.ProtocolDetailView.as_view(),
        name="protocol_detail",
    ),
    path("animals/", views.AnimalListView.as_view(), name="animal_list"),
    path("animals/<int:pk>/", views.AnimalDetailView.as_view(), name="animal_detail"),
    path("tissues/", views.TissueListView.as_view(), name="tissue_list"),
    path("tissues/<int:pk>/", views.TissueDetailView.as_view(), name="tissue_detail"),
    path("samples/", views.SampleListView.as_view(), name="sample_list"),
    path("samples/<int:pk>/", views.SampleDetailView.as_view(), name="sample_detail"),
    path("msruns/", views.MSRunListView.as_view(), name="msrun_list"),
    path("msruns/<int:pk>/", views.MSRunDetailView.as_view(), name="msrun_detail"),
    path(
        "peakgroupsets/", views.PeakGroupSetListView.as_view(), name="peakgroupset_list"
    ),
    path(
        "peakgroupsets/<int:pk>/",
        views.PeakGroupSetDetailView.as_view(),
        name="peakgroupset_detail",
    ),
    path("peakgroups/", views.PeakGroupListView.as_view(), name="peakgroup_list"),
    path(
        "peakgroups/<int:pk>/",
        views.PeakGroupDetailView.as_view(),
        name="peakgroup_detail",
    ),
    path("peakdata/", views.PeakDataListView.as_view(), name="peakdata_list"),
    path("infusates/", views.InfusateListView.as_view(), name="infusate_list"),
    path(
        "infusates/<int:pk>/",
        views.InfusateDetailView.as_view(),
        name="infusate_detail",
    ),
]
