from django.contrib import admin

from .models import Currency, Media, Market, Prediction, Price, NewsMedia, TwitterMedia, RedditMedia


admin.site.register(Currency)
admin.site.register(Media)

admin.site.register(Market)

admin.site.register(Prediction)
admin.site.register(Price)

admin.site.register(NewsMedia)
admin.site.register(TwitterMedia)
admin.site.register(RedditMedia)
