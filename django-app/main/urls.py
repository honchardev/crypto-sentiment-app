from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('currencies/', views.currencies, name='currencies'),
    path('market/', views.market, name='market'),
    path('news/', views.news, name='news'),
    path('dev/', views.dev, name='dev'),
    path('userguide/', views.userguide, name='userguide'),
    path('devguide/', views.devguide, name='devguide'),
    path('apppurpose/', views.apppurpose, name='apppurpose'),
    path('aboutalgo/', views.aboutalgo, name='aboutalgo'),
    path('signup/', views.signup, name='signup'),

    path('api/', views.api_index, name='api_index'),
    path('api/getcurreqscrapedtweetscnt', views.api_getcurreqscrapedtweetscnt, name='api_getcurreqscrapedtweetscnt'),
]
