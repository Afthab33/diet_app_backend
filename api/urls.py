from django.urls import path
from .views import generate_diet

urlpatterns = [
    path("generate-diet/", generate_diet, name="generate_diet"),
]
