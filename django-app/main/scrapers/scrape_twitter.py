import json
import random
import time
import urllib
from datetime import datetime, timedelta

import bs4
import psycopg2
import requests

# URLS to get Twitter search results
TWITTER_SEARCH_URL = 'https://twitter.com/search?q={0}&src=typd&qf=off&l=en'
TWITTER_SEARCH_MORE_URL = 'https://twitter.com/i/search/timeline?q={0}&src=typd&vertical=default&include_available_features=1&include_entities=1&qf=off&l=en&max_position={1}'

# URLs to get Twitter user timeline.
TWITTER_USER_URL = 'https://twitter.com/{0}'
TWITTER_USER_MORE_URL = 'https://twitter.com/i/profiles/show/{0}/timeline/tweets?include_available_features=1&include_entities=1&max_position={1}'

# Different user-agent values to try to overcome bot protection.
user_agent_pool = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0',
    'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393'
]

# Different timeouts to try to overcome bot detection.
timeout_pool_s = [1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]

# Save IDs from database for Currency and Media models.
currency_id_by_ticker = {
    'BTC': 1,
    'ETH': 2,
    'LTC': 3,
    'GENERAL': 4
}
media_id_by_ticker = {
    'Twitter': 1,
    'Reddit': 2,
    'Cnbc': 3,
    'Forbes': 4,
    'Coindesk': 5,
    'Cointelegraph': 6,
    'Ccn': 7,
}

# Default values for sentiment, predictions and trends which identify uninitialized data.
DEFAULT_SENT_SCORE = 100.0


class Tweet(object):
    """Representation of a single tweet from Twitter"""

    def __init__(self, **params):
        self.currencyId_id = params['currencyId_id']
        self.mediaId_id = params['mediaId_id']
        self.tweet_id = params['tweet_id']
        self.content = params['tweet_content']
        self.likes = params['favorite_cnt']
        self.retweets = params['retweet_cnt']
        self.replies = params['reply_cnt']
        self.link = params['tweet_link']
        self.date = params['timestamp']
        self.textblobscore = params['textblobscore']
        self.vaderscore = params['vaderscore']
        self.customclfscore = params['customclfscore']

    def jsonify(self):
        return {
            'currencyId_id': self.currencyId_id,
            'mediaId_id': self.mediaId_id,
            'tweet_id': self.tweet_id,
            'content': self.content,
            'likes': self.likes,
            'retweets': self.retweets,
            'replies': self.replies,
            'link': self.link,
            'date': self.date,
            'textblobscore': self.textblobscore,
            'vaderscore': self.vaderscore,
            'customclfscore': self.customclfscore,
        }

    def __repr__(self):
        return "Tweet {0}".format(" ".join([self.tweet_id, self.date.strftime("%m/%d/%Y, %H:%M:%S")]))


class TwitterTimelineParser(object):
    """Class to hold tools for parsing Twitter timeline into a list of main.scrape_twitter.Tweet instances"""

    def parse_tweets_timeline(self, timeline_html, currencyId_id):
        tweets = []
        soup = bs4.BeautifulSoup(timeline_html, "lxml")
        for tweet_tag in soup.find_all("div", class_="tweet"):
            # Find tweet ID.
            tweet_id = tweet_tag['data-tweet-id']
            # Find content of the tweet.
            tweet_content = tweet_tag.find('p', class_='tweet-text').text
            # Find emojis
            emojis_tags = tweet_tag.find('p', class_='tweet-text').find_all(class_='Emoji')
            tweet_content += " " + " ".join(emoji_tag['alt'] for emoji_tag in emojis_tags)
            # Find favorites, likes and replies cnt.
            tweet_tag_footer_div = tweet_tag.find('div', class_='stream-item-footer')
            favorite_cnt = self.find_tweet_cnt_stats(tweet_tag_footer_div, 'favorite')
            retweet_cnt = self.find_tweet_cnt_stats(tweet_tag_footer_div, 'retweet')
            reply_cnt = self.find_tweet_cnt_stats(tweet_tag_footer_div, 'reply')
            # Find tweet link.
            tweet_link = 'twitter.com{0}'.format(tweet_tag['data-permalink-path'])
            # Find tweet posting timestamp.
            timestamp_unixlike = tweet_tag.find('span', class_='_timestamp')['data-time']
            timestamp = datetime.utcfromtimestamp(int(timestamp_unixlike))
            # Create Tweet class instance to save.
            tweet_instance = Tweet(
                currencyId_id=currencyId_id,
                mediaId_id=media_id_by_ticker['Twitter'],
                tweet_id=tweet_id,
                tweet_content=tweet_content,
                favorite_cnt=favorite_cnt, retweet_cnt=retweet_cnt, reply_cnt=reply_cnt,
                tweet_link=tweet_link,
                timestamp=timestamp,
                textblobscore=DEFAULT_SENT_SCORE,
                vaderscore=DEFAULT_SENT_SCORE,
                customclfscore=DEFAULT_SENT_SCORE
            )
            # Save Tweet class instance.
            tweets.append(tweet_instance)
        return tweets

    @staticmethod
    def find_tweet_cnt_stats(tweet_footer_html, stats_type):
        if stats_type not in ['reply', 'retweet', 'favorite']:
            raise ValueError('Incorrect stats_type value')
        stats_span = tweet_footer_html.find(
            'span', class_='ProfileTweet-action--{0}'.format(stats_type))
        stats_span_value = stats_span.find(
            'span', class_='ProfileTweet-actionCount')['data-tweet-stat-count']
        return stats_span_value


class TwitterScraper(object):
    """Implementation of scraping Twitter search page and user page timelines
    
    scrape_search_timeline - use it for hashtag and keyword searching
        scrapes ~500 tweets

    scrape_userpage_timeline_adv_search - use it when you know the username
        but want only a portion of it's tweets filtered by date.
        Works poorly for long-term search.
        Use it only for 1-2 day range.
        scrapes ~120 tweets for realdonaldtrump and ~50 for WhaleDump

    scrape_userpage_timeline - best for getting last tweets from user.
        scrapes ~700-800 tweets
    """

    def __init__(self):
        self._timeline_parser = TwitterTimelineParser()

    def scrape_search_timeline(self, search_query, currencyId_id):
        # Build a search query.
        search_query = "{0}".format(search_query)
        search_query = urllib.parse.quote(search_query)
        # Start scraping search results page timeline.
        for tweet_bunch in self._scrape_timeline(TWITTER_SEARCH_URL, TWITTER_SEARCH_MORE_URL, search_query, currencyId_id):
            yield tweet_bunch

    def scrape_search_timeline_adv_search(self, search_query, from_datetime, to_datetime, currencyId_id):
        # Build a search query.
        search_query = "{0} since:{1} until:{2}".format(
            search_query,
            from_datetime.strftime("%Y-%m-%d"), to_datetime.strftime("%Y-%m-%d")
        )
        search_query = urllib.parse.quote(search_query)
        # Start scraping search results page timeline.
        is_keyword_search = True
        for tweet_bunch in self._scrape_timeline(TWITTER_SEARCH_URL, TWITTER_SEARCH_MORE_URL, search_query, currencyId_id, is_keyword_search):
            yield tweet_bunch

    def scrape_userpage_timeline(self, username):
        """Please note, that this method could scrape only around 800 last tweets from user page
        This method should be used as a faster approach to scrape selected users's tweets.
        """
        # Start scraping user page timeline.
        currencyId_id = currency_id_by_ticker['GENERAL']
        for tweet_bunch in self._scrape_timeline(TWITTER_USER_URL, TWITTER_USER_MORE_URL, username, currencyId_id):
            yield tweet_bunch

    def scrape_userpage_timeline_adv_search(self, from_username, from_datetime, to_datetime):
        # Build a search query.
        search_query = "from:{0} since:{1} until:{2}".format(
            from_username,
            from_datetime.strftime("%Y-%m-%d"), to_datetime.strftime("%Y-%m-%d")
        )
        search_query = urllib.parse.quote(search_query)
        # Start scraping user's tweets by using advanced search.
        currencyId_id = currency_id_by_ticker['GENERAL']
        adv_search = True
        for tweet_bunch in self._scrape_timeline(TWITTER_SEARCH_URL, TWITTER_SEARCH_MORE_URL, search_query, currencyId_id, adv_search):
            yield tweet_bunch

    def _scrape_timeline(self, first_page_url, more_page_url, main_term, currencyId_id, adv_search=False, is_keyword_search=False):
        # Perform scraping on the first page.
        first_page_tweets_bunch, next_position = self._scrape_first_page(first_page_url, main_term, currencyId_id)
        yield first_page_tweets_bunch
        # Perform scraping on the other pages.
        for nth_page_tweets_bunch in self._scrape_more_pages(more_page_url, main_term, next_position, adv_search, currencyId_id, is_keyword_search):
            yield nth_page_tweets_bunch

    def _scrape_first_page(self, first_page_url, main_term, currencyId_id):
        # Request timeline's 1st page data.
        request_url = first_page_url.format(main_term)
        USER_AGENT = random.choice(user_agent_pool)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_text = response.text
        # Scrape tweets from the 1st page.
        first_page_parsed_tweets = self._timeline_parser.parse_tweets_timeline(response_text, currencyId_id)
        # Find next position argument for the next timeline page.
        next_position = self._find_arg_value(response_text, "data-min-position")
        # Mandatory sleep.
        time.sleep(timeout_pool_s[0])
        return first_page_parsed_tweets, next_position

    def _scrape_more_pages(self, more_page_url, main_term, next_position, adv_search, currencyId_id, is_keyword_search):
        # Vars-helpers for the method
        old_next_position = None
        has_more_items = True  # because bool(next_position) = True
        # Loop while more pages available. Any issue - request data again with the same next_position param.
        while has_more_items:
            try:
                # Request timeline data from Nth page.
                request_url = more_page_url.format(main_term, next_position)
                USER_AGENT = random.choice(user_agent_pool)
                response = requests.get(request_url, headers={'User-agent': USER_AGENT})
                response_text = response.text
                response_dict = json.loads(response_text)
                # Scrape tweets from the Nth page.
                nth_page_parsed_tweets = self._timeline_parser.parse_tweets_timeline(response_dict['items_html'], currencyId_id)
                # Get next_position value for the N+1th page.
                next_position = response_dict.get('min_position', None)
                yield nth_page_parsed_tweets
                # Check if N+1th page exists. If not - exit the function.
                has_more_items = old_next_position != next_position
                if is_keyword_search:
                    if not has_more_items:
                        break
                if not response_dict['has_more_items']:
                    if not has_more_items:
                        break
                    if adv_search:
                        break
                # Save old_next_position for the next N+1th page existence check.
                old_next_position = next_position
                # Sleep for 1-5s before the next request.
                sleep_time = random.choice(timeout_pool_s)
                time.sleep(sleep_time)
            except Exception:
                break

    @staticmethod
    def _find_arg_value(html, value):
        start_pos = html.find(value) + len(value)
        start_pos += 2  # skip = and " characters.
        end_pos = html.find('"', start_pos)
        return html[start_pos:end_pos]


class TwitterScraperPerformer(object):

    def __init__(self):
        # DB connection and cursor instances.
        self.conn = psycopg2.connect()
        self.cur = self.conn.cursor()
        # Saved list of tweets IDs from DB.
        self.existing_tweets_ids = self._get_existing_tweets_ids()
        # Twitter scrapper instance.
        self.twitter_scraper = TwitterScraper()
        # Selected Twitter usernames and hashtags to scrape.
        self.usernames = [
            'VitalikButerin', 'SatoshiLite', 'aantonop', 'ErikVoorhees', 'brian_armstrong', 'cz_binance', 'saifedean',  # influencers
            'binance', 'bitmexdotcom', 'bitfinex', 'coinbase', 'cex_io', 'krakenfx',  # cryptocurrency exchanges
            'bitmexresearch', 'wizsecurity', 'proofofresearch',  # research pages
            'VentureCoinist', 'notsofast', 'Cryptopia_NZ', 'BTC_Revolution', 'FelixOHartmann', 'CryptoMoshing', 'cryptotraderpro',  # cryptocurrency traders
            'bitcoin', 'ethereum', 'litecoin',  # "official" cryptocurrency accounts
        ]
        # Initialize hashtags, tags and keywords to scrape
        self.ticker_hashtags_tags = {
            'BTC': ["#btc", "#Bitcoin", "$btc"],
            'ETH': ["#eth", "#Ethereum", "$eth"],
            'LTC': ['#ltc', "#Litecoin", "$ltc"],
            'GENERAL': ['#cryptocurrency', "#crypto"]
        }
        # The earliest date to scrape.
        self.earliest_date = datetime(2016, 1, 1)

    def scrape_last_updated_data(self):
        # Update local storage of already saved tweets.
        self.existing_tweets_ids = self._get_existing_tweets_ids()
        # Container to save new scraped data.
        data_container = []
        # Perform scraping by date range.
        # 1. Perform scraping by username.
        for username in self.usernames:
            for tweet_bunch in self.twitter_scraper.scrape_userpage_timeline(username):
                skip_user = False
                for tweet in tweet_bunch:
                    if tweet.tweet_id not in self.existing_tweets_ids:
                        self._save_tweet(tweet)
                        data_container.append(tweet)
                    else:
                        skip_user = True
                        break
                if skip_user is True:
                    print('DBG: skip user {0}\n'.format(username))
                    break
        # Update local storage of existing tweets ids.
        self.existing_tweets_ids = self._get_existing_tweets_ids()
        # 2. Perform scraping by keywords.
        for ticker, search_terms in self.ticker_hashtags_tags.items():
            currencyId_id = currency_id_by_ticker[ticker]
            for search_term in search_terms:
                for tweet_bunch in self.twitter_scraper.scrape_search_timeline(search_term, currencyId_id):
                    skip_search_term = False
                    for tweet in tweet_bunch:
                        if tweet.tweet_id not in self.existing_tweets_ids:
                            self._save_tweet(tweet)
                            data_container.append(tweet)
                        else:
                            skip_search_term = True
                            break
                    if skip_search_term is True:
                        print('DBG: skip search term {0}\n'.format(search_term))
                        break
        # Return data and status for webpage view.
        return {
            'status': 'OK',
            'data': data_container
        }

    def scrape_date_range_data(self, from_date, to_date):
        # Check if from_date is no older than the earliest date allowed.
        if from_date < self.earliest_date:
            from_date = self.earliest_date
        # Update local storage of already saved tweets.
        self.existing_tweets_ids = self._get_existing_tweets_ids()
        # Container to save new scraped data.
        data_container = []
        # Perform scraping by date range.
        # 1. Perform scraping by username.
        for username in self.usernames:
            print('Start scraping {0}\n'.format(username))
            for tweet_bunch in self.twitter_scraper.scrape_userpage_timeline_adv_search(username, from_date, to_date):
                print('Go to next bunch for {0}'.format(username))
                for tweet in tweet_bunch:
                    if tweet.tweet_id not in self.existing_tweets_ids:
                        self._save_tweet(tweet)
                        data_container.append(tweet)
                    else:
                        continue
        # Update local storage of existing tweets ids.
        self.existing_tweets_ids = self._get_existing_tweets_ids()
        # 2. Perform scraping by keywords.
        for ticker, search_terms in self.ticker_hashtags_tags.items():
            currencyId_id = currency_id_by_ticker[ticker]
            for search_term in search_terms:
                print('Start scraping {0}\n'.format(search_term))
                for tweet_bunch in self.twitter_scraper.scrape_search_timeline_adv_search(search_term, from_date, to_date, currencyId_id):
                    print('Go to next bunch for {0}'.format(search_term))
                    for tweet in tweet_bunch:
                        if tweet.tweet_id not in self.existing_tweets_ids:
                            self._save_tweet(tweet)
                            data_container.append(tweet)
                        else:
                            continue
        # Return data and status for webpage view.
        return {
            'status': 'OK',
            'data': data_container
        }

    def _get_existing_tweets_ids(self):
        # Save Tweet IDs
        self.cur.execute("""select tweet_id from main_twittermedia;""")
        existing_tweets_fromdb = self.cur.fetchall()
        existing_tweets_ids = [row[0] for row in existing_tweets_fromdb]
        return existing_tweets_ids

    def _save_tweet(self, tweet):
        insert_query = """
            INSERT INTO main_twittermedia
            ("mediaId_id", "currencyId_id", tweet_id, content, likes, retweets, replies, link, date, textblobscore, vaderscore, customclfscore)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
        insert_query_fields = (
            tweet.mediaId_id, tweet.currencyId_id,
            tweet.tweet_id,
            tweet.content,
            tweet.likes, tweet.retweets, tweet.replies,
            tweet.link,
            tweet.date,
            tweet.textblobscore, tweet.vaderscore, tweet.customclfscore
        )
        self.cur.execute(insert_query, insert_query_fields)
        self.conn.commit()
        print('DBG INSERT: inserted {0}'.format(tweet))


def __dbg():
    ts = TwitterScraper()
    from_date = datetime(2018, 5, 29)
    to_date = datetime(2018, 5, 30)
    general_currencyId_id = currency_id_by_ticker['GENERAL']
    btc_currencyId_id = currency_id_by_ticker['BTC']
    tweets_container = []
    # for tweet_bunch in ts.scrape_search_timeline('#bitcoin', btc_currencyId_id):
    # for tweet_bunch in ts.scrape_search_timeline_adv_search("#bitcoin", from_date, to_date, btc_currencyId_id):
    # for tweet_bunch in ts.scrape_userpage_timeline_adv_search('WhalePanda', from_date, to_date):
    for tweet_bunch in ts.scrape_userpage_timeline('notsofast'):
        tweets_container.extend(tweet_bunch)


def __dbg_db():
    from_date = datetime(2018, 5, 29)
    to_date = datetime(2018, 5, 30)
    tsp = TwitterScraperPerformer()
    resp = tsp.scrape_last_updated_data()
    resp = tsp.scrape_date_range_data(from_date, to_date)


def __dbg_truncate_db():
    try:
        conn = psycopg2.connect()
        cur = conn.cursor()
        cur.execute("""TRUNCATE TABLE  main_twittermedia;""")
        conn.commit()
        print('Successfully truncated main_twittermedia')
    except (Exception, psycopg2.Error) as e:
        print('Couldn\'t truncate main_twittermedia table. Error: {0}'.format(e))


def __historical_big_date_range():
    tsp = TwitterScraperPerformer()
    date_from = datetime(2017, 8, 1)
    date_to = datetime.now()
    while date_from < date_to:
        date_from_plus_1d = date_from + timedelta(days=1)
        tsp.scrape_date_range_data(date_from, date_from_plus_1d)
        date_from = date_from_plus_1d
