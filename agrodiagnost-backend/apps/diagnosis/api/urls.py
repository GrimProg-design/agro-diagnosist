"""
АгроДиагност — diagnosis app URL patterns.
"""
from django.urls import path

from apps.diagnosis.views import DiagnosisView, MaturityView

app_name = "diagnosis"

urlpatterns = [
    path("diagnosis/", DiagnosisView.as_view(), name="diagnose"),
    path("maturity/", MaturityView.as_view(), name="maturity"),
]
