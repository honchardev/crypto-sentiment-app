from django.urls import path

from . import views


urlpatterns = [
    path('api/', views.api_index, name='api_index'),
    path('api/getcurreqscrapedtweetscnt', views.api_getcurreqscrapedtweetscnt, name='api_getcurreqscrapedtweetscnt'),
]
