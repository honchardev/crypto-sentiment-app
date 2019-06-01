import json
import random
import time
import urllib
from datetime import datetime

import bs4
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


class Tweet(object):
    """Representation of a single tweet from Twitter"""

    def __init__(self, **params):
        self.tweet_id = params['tweet_id']
        self.content = params['tweet_content']
        self.likes = params['favorite_cnt']
        self.retweets = params['retweet_cnt']
        self.replies = params['reply_cnt']
        self.link = params['tweet_link']
        self.date = params['timestamp']

    def jsonify(self):
        tweet_dict = {
            'tweet_id': self.tweet_id,
            'content': self.content,
            'likes': self.likes,
            'retweets': self.retweets,
            'replies': self.replies,
            'link': self.link,
            'date': self.date
        }
        return tweet_dict

    def __repr__(self):
        return "Tweet {0}".format(" ".join([self.tweet_id, self.content, self.link, self.date]))


class TwitterTimelineParser(object):
    """Class to hold tools for parsing Twitter timeline into a list of main.scrape_twitter.Tweet instances"""

    def parse_tweets_timeline(self, timeline_html):
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
            tweet_instance = Tweet(tweet_id=tweet_id, tweet_content=tweet_content,
                                   favorite_cnt=favorite_cnt, retweet_cnt=retweet_cnt, reply_cnt=reply_cnt,
                                   tweet_link=tweet_link,
                                   timestamp=timestamp)
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
        self._last_req_scraped_tweets_cnt = 0

    def scrape_search_timeline_adv_search(self, search_query, from_datetime, to_datetime):
        # Build a search query.
        search_query = "{0} since:{1} until:{2}".format(
            search_query,
            from_datetime.strftime("%Y-%m-%d"), to_datetime.strftime("%Y-%m-%d")
        )
        search_query = urllib.parse.quote(search_query)
        # Start scraping search results page timeline.
        scraped_tweets = self._scrape_timeline(TWITTER_SEARCH_URL, TWITTER_SEARCH_MORE_URL, search_query)
        return scraped_tweets

    def scrape_search_timeline(self, search_query):
        # Build a search query.
        search_query = "{0}".format(search_query)
        search_query = urllib.parse.quote(search_query)
        # Start scraping search results page timeline.
        scraped_tweets = self._scrape_timeline(TWITTER_SEARCH_URL, TWITTER_SEARCH_MORE_URL, search_query)
        return scraped_tweets

    def scrape_userpage_timeline_adv_search(self, from_username, from_datetime, to_datetime):
        # Build a search query.
        search_query = "from:{0} since:{1} until:{2}".format(
            from_username,
            from_datetime.strftime("%Y-%m-%d"), to_datetime.strftime("%Y-%m-%d")
        )
        search_query = urllib.parse.quote(search_query)
        # Start scraping user's tweets by using advanced search.
        adv_search = True
        scraped_tweets = self._scrape_timeline(TWITTER_SEARCH_URL, TWITTER_SEARCH_MORE_URL, search_query, adv_search)
        return scraped_tweets

    def scrape_userpage_timeline(self, username):
        """Please note, that this method could scrape only 700-800 last tweets from user page
        This method could only be used as a faster approach to scrape selected users's tweets.
        """
        # Start scraping user page timeline.
        scraped_tweets = self._scrape_timeline(TWITTER_USER_URL, TWITTER_USER_MORE_URL, username)
        return scraped_tweets

    def get_last_scraped_tweets_cnt(self):
        return self._last_req_scraped_tweets_cnt

    @staticmethod
    def _find_arg_value(html, value):
        start_pos = html.find(value) + len(value)
        start_pos += 2  # skip = and " characters.
        end_pos = html.find('"', start_pos)
        return html[start_pos:end_pos]

    def _scrape_timeline(self, first_page_url, more_page_url, main_term, adv_search=False):
        # Refresh last request scraped tweets count.
        self._last_req_scraped_tweets_cnt = 0
        # Storage for scraped tweets.
        scraped_tweets = []
        # Perform scraping on the first page.
        first_page_parsed_tweets, next_position = self._scrape_first_page(first_page_url, main_term)
        # Save scraped tweets.
        scraped_tweets.extend(first_page_parsed_tweets)
        # Perform scraping on the other pages.
        if next_position:
            other_pages_parsed_tweets = self._scrape_more_pages(more_page_url, main_term, next_position, adv_search)
            scraped_tweets.extend(other_pages_parsed_tweets)
        return scraped_tweets

    def _scrape_first_page(self, first_page_url, main_term):
        # Request timeline's 1st page data.
        request_url = first_page_url.format(main_term)
        USER_AGENT = random.choice(user_agent_pool)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_text = response.text
        # Scrape tweets from the 1st page.
        first_page_parsed_tweets = self._timeline_parser.parse_tweets_timeline(response_text)
        # Find next position argument for the next timeline page.
        next_position = self._find_arg_value(response_text, "data-min-position")
        # Update last request scraped tweets count.
        self._last_req_scraped_tweets_cnt += len(first_page_parsed_tweets)
        # Mandatory sleep.
        time.sleep(timeout_pool_s[0])
        return first_page_parsed_tweets, next_position

    def _scrape_more_pages(self, more_page_url, main_term, next_position, adv_search):
        # Vars-helpers for the method
        old_next_position = None
        has_more_items = True  # because bool(next_position) = True
        # Storage for scraped tweets
        scraped_tweets = []
        # Loop while more pages available. Any issue - request data again with the same next_position param.
        while has_more_items:
            try:
                # Request timeline data from Nth page.
                request_url = more_page_url.format(main_term, next_position)
                USER_AGENT = random.choice(user_agent_pool)
                print('DBG: Trying to get response from requests.get...')
                response = requests.get(request_url, headers={'User-agent': USER_AGENT})
                response_text = response.text
                response_dict = json.loads(response_text)
                # Scrape tweets from the Nth page.
                nth_page_parsed_tweets = self._timeline_parser.parse_tweets_timeline(response_dict['items_html'])
                scraped_tweets.extend(nth_page_parsed_tweets)
                # Update last request scraped tweets count.
                self._last_req_scraped_tweets_cnt += len(nth_page_parsed_tweets)
                # Get next_position value for the N+1th page.
                next_position = response_dict.get('min_position', None)
                # Check if N+1th page exists. If not - exit the function.
                has_more_items = old_next_position != next_position
                if not response_dict['has_more_items']:
                    if not has_more_items:
                        break
                    if adv_search:
                        break
                # Save old_next_position for the next N+1th page existence check.
                old_next_position = next_position
                # Display DBG info about current Nth page.
                print('DBG: old==next: {0}'.format(old_next_position != next_position))
                print('DBG: FRI is {0}'.format(response_dict.get('focused_refresh_interval', None)))
                print('DBG: tweets scraped: {0}'.format(self._last_req_scraped_tweets_cnt))
                print('DBG: last scraped tweet date: {0}'.format(scraped_tweets[-1].date))
                # Sleep for 1-5s before the next request.
                sleep_time = random.choice(timeout_pool_s)
                print('DBG: waiting for {0}s\n'.format(sleep_time))
                time.sleep(sleep_time)
            except Exception as e:
                print('DBG: Exception skipped in scrape_twitter.TwitterScraper._scrape_more_pages')
                print('DBG: {0}'.format(e))
                break
        print('DBG: finished scraping Nth pages.')
        return scraped_tweets


def __dbg():
    ts = TwitterScraper()
    from_date = datetime(2018, 5, 1)
    to_date = datetime(2019, 5, 30)
    tweets = ts.scrape_search_timeline_adv_search("#bitcoin", from_date, to_date)
    tweets = ts.scrape_search_timeline('#bitcoin')
    tweets = ts.scrape_userpage_timeline('realdonaldtrump')
    tweets = ts.scrape_userpage_timeline_adv_search('WhalePanda', from_date, to_date)
    print(tweets[:5], len(tweets))
