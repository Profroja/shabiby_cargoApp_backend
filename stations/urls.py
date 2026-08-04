from django.urls import path

from .views import CargoCenterDetailView, CargoCenterListView

urlpatterns = [
    path("", CargoCenterListView.as_view(), name="cargo-center-list"),
    path("<str:pk>/", CargoCenterDetailView.as_view(), name="cargo-center-detail"),
]
