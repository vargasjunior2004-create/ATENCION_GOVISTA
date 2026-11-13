from django.urls import path

from .views import RetirementDocumentExtractView


urlpatterns = [
    path('extract-retirement/', RetirementDocumentExtractView.as_view()),
]
