from django.utils import timezone

from django.http import JsonResponse


def index(req):
    resp_data = {
        'status': 'OK',
        'v': 0.01,
        'time': timezone.now(),
        'msg': 'Welcome to sentpredapp API!',
    }
    return JsonResponse(resp_data)
