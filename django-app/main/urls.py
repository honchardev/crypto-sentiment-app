from django.urls import path
from django.views.generic import TemplateView

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('currencies/', views.currencies, name='currencies'),
    path('market/', views.market, name='market'),
    path('news/', views.news, name='news'),
    path('dev/', views.dev, name='dev'),
    path('signup/', views.signup, name='signup'),

    path('userguide/', TemplateView.as_view(template_name='userguide.html'), name='userguide'),
    path('devguide/', TemplateView.as_view(template_name='devguide.html'), name='devguide'),
    path('apppurpose/', TemplateView.as_view(template_name='apppurpose.html'), name='apppurpose'),
    path('aboutalgo/', TemplateView.as_view(template_name='aboutalgo.html'), name='aboutalgo'),

    path('api/', views.api_index, name='api_index'),
    path('api/getcurreqscrapedtweetscnt', views.api_getcurreqscrapedtweetscnt, name='api_getcurreqscrapedtweetscnt'),
]
