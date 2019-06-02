import json
from datetime import datetime, timedelta
import os

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

cryptocompare_api_key = os.environ['CRYPTOCOMPARE_API_KEY']

HISTORICAL_PRICE_HOUR = 'https://min-api.cryptocompare.com/data/histohour?fsym={0}&tsym=USD&extraParams=sentpredapp&limit=2000&api_key={1}'
CURRENT_PRICE_FULL = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,LTC&tsyms=USD&extraParams=sentpredapp&api_key={0}"
GLOBAL_MC_VOL = "https://graphs2.coinmarketcap.com/global/marketcap-total/{0}/{1}/"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

# Cryptocurrencies' IDs from main_currency table.
cryptocurrency_id_by_ticker = {
    'BTC': 1,
    'ETH': 2,
    'LTC': 3
}

# Default values for sentiment, predictions and trends which identify uninitialized data.
DEFAULT_SENT_VALUE = 100.0
DEFAULT_PRED_VALUE = 101.0
DEFAULT_TREND_VALUE = 102.0


class MarketData(object):
    """Reprensetation of main_market table entry."""

    def __init__(self, **params):
        self.date = params.get('date')
        self.globalmarketcap = params.get('globalmarketcap')
        self.globalvolume = params.get('globalvolume')
        self.mchoursentiment = params.get('mchoursentiment')
        self.mchourprediction = params.get('mchourprediction')
        self.mchourtrend = params.get('mchourtrend')


class PriceData(object):
    """Representation of main_price table entry."""

    def __init__(self, **params):
        self.date = params.get('date')
        self.openprice = params.get('openprice')
        self.closeprice = params.get('closeprice')
        self.highprice = params.get('highprice')
        self.lowprice = params.get('lowprice')
        self.spreadvalue = params.get('spreadvalue')
        self.returnvalue = params.get('returnvalue')
        self.volumeto = params.get('volumeto')
        self.currency_id = params.get('currency_id')


class MarketDataScraper(object):

    @staticmethod
    def scrape_current_data():
        """Scrape current marketcap and global volume values."""
        # From: now-60min. To: now+10min
        now = datetime.now()
        from_date = now - timedelta(minutes=60)
        to_date = now + timedelta(minutes=10)
        # Build request URL
        from_date_unix_ms = int(from_date.timestamp() * 1000)
        to_date_unix_ms = int(to_date.timestamp() * 1000)
        request_url = GLOBAL_MC_VOL.format(from_date_unix_ms, to_date_unix_ms)
        # Send a request & collect raw response text
        print('DBG: Trying to get response from requests.get...')
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_text = response.text
        response_dict = json.loads(response_text)
        # Get last global volume and mktcap values.
        last_mktcap_value = response_dict['market_cap_by_available_supply'][-1][1]
        last_volume_value = response_dict['volume_usd'][-1][1]
        last_date_timestamp = int(response_dict['volume_usd'][-1][0] / 1000)
        last_date_value = datetime.fromtimestamp(last_date_timestamp)
        print('DBG: Scraped last data at {0}: mktcap:{1} volume:{2}'.format(
            last_date_value, last_mktcap_value, last_volume_value))
        return last_date_value, last_mktcap_value, last_volume_value

    @staticmethod
    def scrape_historical_data(from_date, to_date):
        """Scrape data by month. Note, that future month could be used as a final month."""
        # Container to save mktcap values.
        mkdata_container = []
        # Fix to_date so that max data should be a month further but data will be in hourly format, not with lower interval.
        to_date = to_date + relativedelta(months=1)
        to_date = datetime(to_date.year, to_date.month, 1, 0, 0, 1)
        # toFix: now you can only use it properly if to_date=datetime.now().
        # Same fix for from_date: avoid missing saving first value.
        from_date = from_date - timedelta(minutes=from_date.minute)
        from_date = from_date - timedelta(seconds=from_date.second)
        from_date = from_date + timedelta(seconds=1)
        # Scrape all the historical data.
        cur_date = from_date
        while cur_date < to_date:
            # Build request URL
            request_from_date_unix_ms = int(cur_date.timestamp() * 1000)
            cur_date += relativedelta(months=1)  # Note: cur_date is changed here
            if cur_date > to_date:
                cur_date = to_date + timedelta(minutes=5)
            request_to_date_unix_ms = int(cur_date.timestamp() * 1000)
            request_url = GLOBAL_MC_VOL.format(request_from_date_unix_ms, request_to_date_unix_ms)
            # Send a request & collect raw response text
            print('DBG: Trying to get response from requests.get...')
            response = requests.get(request_url, headers={'User-agent': USER_AGENT})
            response_text = response.text
            response_dict = json.loads(response_text)
            # Load volume and mktcap data.
            global_mktcap_data = response_dict.get('market_cap_by_available_supply', None)
            global_volume_data = response_dict.get('volume_usd', None)
            if global_mktcap_data and global_volume_data:
                # Save data as MarketData instance.
                for mktcap_data, vol_data in zip(global_mktcap_data, global_volume_data):
                    marketdata_obj = MarketData(
                        date=datetime.fromtimestamp(int(mktcap_data[0] / 1000)),
                        globalmarketcap=mktcap_data[1],
                        globalvolume=vol_data[1],
                        mchoursentiment=DEFAULT_SENT_VALUE,  # fake data
                        mchourprediction=DEFAULT_PRED_VALUE,  # fake data
                        mchourtrend=DEFAULT_TREND_VALUE  # fake data
                    )
                    mkdata_container.append(marketdata_obj)
            print('DBG: saved mktcap and glbl_volume data from {0} to {1}'.format(
                datetime.fromtimestamp(request_from_date_unix_ms / 1000),
                datetime.fromtimestamp(request_to_date_unix_ms / 1000)
            ))
            print('DBG: {0} items in total were saved\n'.format(len(mkdata_container)))
        # Final awkward fix: if last two values share the same hour value - remove the last element.
        if mkdata_container[-1].date.hour == mkdata_container[-2].date.hour:
            del mkdata_container[-1]
        print('DBG: MarketDataScraper.scrape_historical_data scraped {0} items\n'.format(len(mkdata_container)))
        return mkdata_container


class PriceDataScraper(object):

    def scrape_historical_data(self, ticker, from_date):
        """Get ticker_name historical OHLCV data. Note, that function starts at datetime.now."""
        # Container to save historical financial data.
        findata_container = []
        # Make first request - the earliest data.
        print('DBG: Trying to get response from requests.get...')
        request_url = HISTORICAL_PRICE_HOUR.format(ticker, cryptocompare_api_key)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_dict = json.loads(response.text)
        # Get Price data from the first request.
        first_response_data = response_dict['Data'][::-1]
        from_date_unixtime = int(from_date.timestamp())
        print('DBG: Scraped {0} data points from {1} to {2}'.format(
            len(first_response_data),
            datetime.fromtimestamp(first_response_data[0]['time']),
            datetime.fromtimestamp(first_response_data[-1]['time'])
        ))
        for item in first_response_data:
            if item['time'] < from_date_unixtime:
                print('DBG: Exiting at {0} date.'.format(datetime.fromtimestamp(item['time'])))
                return findata_container
            pricedata_to_add = self._cryptocompare_item_to_pricedata(item, ticker)
            findata_container.append(pricedata_to_add)
        print('DBG: Saved {0} data points with dates range from {1} to {2}\n'.format(
            len(findata_container), findata_container[0].date, findata_container[-1].date))
        # first toTs value - the earliest timestamp received from first request.
        toTs = response_dict.get('TimeFrom', None)
        # Scrape historical data depending on tS parameter
        to_break = False
        while toTs:
            # Make Nth request.
            request_url = HISTORICAL_PRICE_HOUR.format(ticker, cryptocompare_api_key)
            request_url += "&toTs={0}".format(toTs)
            print('DBG: Trying to get response from requests.get...')
            response = requests.get(request_url, headers={'User-agent': USER_AGENT})
            response_dict = json.loads(response.text)
            # Get Price data from the Nth request.
            nth_response_data = response_dict['Data'][:-1][::-1]
            print('DBG: Scraped {0} data points from {1} to {2}'.format(
                len(nth_response_data),
                datetime.fromtimestamp(nth_response_data[0]['time']),
                datetime.fromtimestamp(nth_response_data[-1]['time'])
            ))
            for item in nth_response_data:
                # Check if we need any more data from current Nth page.
                if item['time'] < from_date_unixtime:
                    print('DBG: Exiting at {0} date.'.format(datetime.fromtimestamp(item['time'])))
                    to_break = True
                    break
                pricedata_to_add = self._cryptocompare_item_to_pricedata(item, ticker)
                findata_container.append(pricedata_to_add)
            print('DBG: findata_container date range is from {0} to {1}'.format(
                findata_container[0].date, findata_container[-1].date))
            print('DBG: findata_container size is {0}\n'.format(len(findata_container)))
            # Check if we need any more data from any other pages.
            if to_break:
                break
            # Update toTs value
            toTs = response_dict.get('TimeFrom', None)
        print('DBG: Returning container with size of {0}\n'.format(len(findata_container)))
        return findata_container

    @staticmethod
    def scrape_current_data():
        """Get BTC, LTC and ETH current full data, not only OHLCV."""
        # Send a request & collect raw response text
        print('DBG: Trying to get response from requests.get...')
        request_url = CURRENT_PRICE_FULL.format(cryptocompare_api_key)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_text = response.text
        response_dict = json.loads(response_text)
        # Get raw data, erase same data for display.
        raw_data = response_dict['RAW']
        # Return all the data from cryptocompare response.
        print('Scraped FULL data about btc, eth and ltc')
        return {
            'BTC': raw_data['BTC']['USD'],
            'ETH': raw_data['ETH']['USD'],
            'LTC': raw_data['LTC']['USD']
        }

    @staticmethod
    def _cryptocompare_item_to_pricedata(item, ticker):
        price_data = PriceData(
            date=datetime.fromtimestamp(item['time']),
            openprice=item['open'],
            closeprice=item['close'],
            highprice=item['high'],
            lowprice=item['low'],
            spreadvalue=item['high'] - item['low'],
            returnvalue=item['open'] - item['close'],
            volumeto=item['volumeto'],
            currency_id=cryptocurrency_id_by_ticker[ticker]
        )
        return price_data


def __dbg():
    from_date = datetime(2018, 1, 1)
    to_date = datetime(2019, 6, 1)

    mdscraper = MarketDataScraper()
    scraped_data = mdscraper.scrape_current_data()
    scraped_data = mdscraper.scrape_historical_data(from_date, to_date)

    pdscrapper = PriceDataScraper()
    scraped_data = pdscrapper.scrape_current_data()
    scraped_data = pdscrapper.scrape_historical_data('BTC', from_date)

    print(scraped_data)
