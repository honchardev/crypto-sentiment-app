from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.http import HttpResponse

from .scrapers.scrape_twitter import TwitterScraper


twitter_scrapper = TwitterScraper()


def index(req):
    return render(req, 'index.html')


def currencies(req):
    context = {
        'currencies_page_active': True
    }
    return render(req, 'currencies.html', context=context)


def market(req):
    context = {
        'market_page_active': True
    }
    return render(req, 'market.html', context=context)


def news(req):
    context = {
        'news_page_active': True
    }
    return render(req, 'news.html', context=context)


@login_required
def dev(req):
    return render(req, 'dev.html')


def userguide(req):
    return render(req, 'userguide.html')


def devguide(req):
    return render(req, 'devguide.html')


def apppurpose(req):
    return render(req, 'apppurpose.html')


def aboutalgo(req):
    return render(req, 'aboutalgo.html')


@login_required
def signup(req):
    if not req.user.is_superuser:
        return redirect('index')
    context = {}
    if req.method == 'POST':
        form = UserCreationForm(req.POST)
        if form.is_valid():
            form.save()
            context['form'] = form
            context['status'] = True
            context['new_user_username'] = form.cleaned_data.get('username')
        else:
            context['status'] = False
    else:
        form = UserCreationForm()
        context['form'] = form
    return render(req, 'signup.html', context=context)


def api_index(req):
    resp_data = {
        'status': 'OK',
        'v': 0.01,
        'time': timezone.now(),
        'msg': 'Welcome to sentpredapp API!',
    }
    return JsonResponse(resp_data)


def api_getcurreqscrapedtweetscnt(req):
    resp_data = {
        'status': 'OK',
        'cnt': twitter_scrapper.get_last_scraped_tweets_cnt()
    }
    return JsonResponse(resp_data)
