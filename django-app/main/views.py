import json
import time
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ratelimit.decorators import ratelimit

from .preprocessors.findata_preprocessor import (MarketDataCleaner,
                                                 PriceDataCleaner)
from .scrapers.scrape_fin import (FinScraperPerformer, MarketDataScraper,
                                  PriceDataScraper)
from .scrapers.scrape_twitter import TwitterScraperPerformer

twitter_scraper_performer = TwitterScraperPerformer()
fin_scraper_performer = FinScraperPerformer()

marketdata_scraper = MarketDataScraper()
pricedata_scraper = PriceDataScraper()


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
    users = User.objects.all()
    context = {
        'dev_page_active': True,
        'users': users
    }
    return render(req, 'dev.html', context=context)


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


@ratelimit(key='ip', rate='10/m')
def api_index(req):
    resp_data = {
        'status': 'OK',
        'v': 0.01,
        'time': timezone.now(),
        'msg': 'Welcome to sentpredapp API!',
    }
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
def api_get_market_last(req):
    resp_data = {}
    if req.method == 'GET':
        today_data = []
        for mkt_data in marketdata_scraper.scrape_today_data():
            today_data.append(mkt_data)
        today_data_jsonified = [data.jsonify() for data in today_data]
        resp_data = {
            'status': 'OK',
            'data': today_data_jsonified
        }
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
def api_get_price_last(req):
    resp_data = {}
    if req.method == 'GET':
        full_data = pricedata_scraper.scrape_current_full_data()
        resp_data = {
            'status': 'OK',
            'data': full_data
        }
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
def api_get_tweets_last(req):
    resp_data = {}
    if req.method == 'GET':
        tweets = twitter_scraper_performer.get_last_tweets(20)
        tweets_jsonified = [tweet.jsonify() for tweet in tweets]
        resp_data = {
            'status': 'OK',
            'data': tweets_jsonified
        }
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
def api_get_reddit_last(req):
    resp_data = {}
    if req.method == 'GET':
        # todo:
        resp_data['status'] = 'OK'
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
def api_get_news_last(req):
    resp_data = {}
    if req.method == 'GET':
        # todo:
        resp_data['status'] = 'OK'
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
@csrf_exempt
def api_update_last_data(req):
    resp_data = {}
    if req.method == 'POST':
        post_req_dict = req.POST
        button_id = post_req_dict['btn_id']
        if button_id == "updTwitterLast":
            resp_data = twitter_scraper_performer.scrape_last_updated_data()
            resp_data_jsonified = [tweet.jsonify() for tweet in resp_data['data']]
            resp_data['data'] = resp_data_jsonified
        elif button_id == "updRedditLast":
            pass
        elif button_id == "updNewsLast":
            pass
        elif button_id == "updFinGlobalLast":
            resp_data = fin_scraper_performer.scrape_market_data()
            resp_data_jsonified = [data.jsonify() for data in resp_data['data']]
            resp_data['data'] = resp_data_jsonified
        elif button_id == "updFinCurrenciesLast":
            resp_data = fin_scraper_performer.scrape_price_data()
            resp_data_jsonified = [data.jsonify() for data in resp_data['data']]
            resp_data['data'] = resp_data_jsonified
        else:
            resp_data['status'] = 'FAIL'
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)


@ratelimit(key='ip', rate='10/m')
@csrf_exempt
def api_update_range_data(req):
    resp_data = {}
    if req.method == 'POST':
        post_req_dict = req.POST
        print('\n{0}\n'.format(post_req_dict))
        if not post_req_dict['btn_id'] or not post_req_dict['from_time'] or not post_req_dict['to_time']:
            resp_data['status'] = 'FAIL'
            return JsonResponse(resp_data)
        from_date = datetime.strptime(post_req_dict['from_time'], "%m/%d/%Y")
        to_date = datetime.strptime(post_req_dict['to_time'], "%m/%d/%Y")
        button_id = post_req_dict['btn_id']
        if button_id == "updTwitterRange":
            resp_data = twitter_scraper_performer.scrape_date_range_data(from_date, to_date)
            resp_data_jsonified = [tweet.jsonify() for tweet in resp_data['data']]
            resp_data['data'] = resp_data_jsonified
            # todo: clean twitter data
        elif button_id == "updRedditRange":
            pass
        elif button_id == "updNewsRange":
            pass
        else:
            resp_data['status'] = 'FAIL'
    else:
        resp_data['status'] = 'FAIL'
    return JsonResponse(resp_data)
