from django.utils import timezone

from django.db import models


class Currency(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    shortdescr = models.TextField()
    description = models.TextField()


class Media(models.Model):
    link = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    shortdescr = models.TextField()
    description = models.TextField()


class Market(models.Model):
    date = models.DateTimeField(default=timezone.now)
    marketcap = models.FloatField()
    mchoursentiment = models.FloatField()
    mchourprediction = models.FloatField()
    mchourtrend = models.FloatField()


class Prediction(models.Model):
    currencyId = models.ForeignKey(Currency, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    hourprediction = models.FloatField()
    daypredictioon = models.FloatField()
    weekprediction = models.FloatField()
    monthprediction = models.FloatField()
    hoursentiment = models.FloatField()
    hourbullish = models.FloatField()
    hourbearish = models.FloatField()


class Price(models.Model):
    currencyId = models.ForeignKey(Currency, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    openprice = models.FloatField()
    highprice = models.FloatField()
    lowprice = models.FloatField()
    closeprice = models.FloatField()
    spreadvalue = models.FloatField()
    returnvalue = models.FloatField() 


class NewsMedia(models.Model):
    currencyId = models.ForeignKey(Currency, on_delete=models.CASCADE)
    mediaId = models.ForeignKey(Media, on_delete=models.CASCADE)
    content = models.TextField()
    headline = models.CharField(max_length=512)
    link = models.CharField(max_length=512)
    date = models.DateTimeField()
    textblobscore = models.FloatField()
    vaderscore = models.FloatField()
    customclfscore = models.FloatField()


class TwitterMedia(models.Model):
    currencyId = models.ForeignKey(Currency, on_delete=models.CASCADE)
    mediaId = models.ForeignKey(Media, on_delete=models.CASCADE)
    tweet_id = models.CharField(max_length=100)
    content = models.TextField()
    likes = models.IntegerField()
    retweets = models.IntegerField()
    replies = models.IntegerField()
    link = models.CharField(max_length=512)
    date = models.DateTimeField()
    textblobscore = models.FloatField()
    vaderscore = models.FloatField()
    customclfscore = models.FloatField()


class RedditMedia(models.Model):
    currencyId = models.ForeignKey(Currency, on_delete=models.CASCADE)
    mediaId = models.ForeignKey(Media, on_delete=models.CASCADE)
    headline = models.CharField(max_length=512)
    upvotes = models.IntegerField()
    comments = models.IntegerField()
    shares = models.IntegerField()
    link = models.CharField(max_length=512)
    date = models.DateTimeField()
    textblobscore = models.FloatField()
    vaderscore = models.FloatField()
    customclfscore = models.FloatField()
