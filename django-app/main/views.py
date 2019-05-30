from django.http import JsonResponse
from django.utils import timezone

from .scrapers.scrape_twitter import TwitterScraper


twitter_scrapper = TwitterScraper()


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
