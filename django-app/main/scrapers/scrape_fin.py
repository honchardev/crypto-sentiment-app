import json
import time
from datetime import datetime, timedelta
import os

import psycopg2
import requests
from dateutil.relativedelta import relativedelta

cryptocompare_api_key = os.environ.get('cryptocompare_api_key')

GLOBAL_MC_VOL = "https://graphs2.coinmarketcap.com/global/marketcap-total/{0}/{1}/"
HISTORICAL_PRICE_HOUR = 'https://min-api.cryptocompare.com/data/histohour?fsym={0}&tsym=USD&extraParams=sentpredapp&limit=2000&api_key={1}'
CURRENT_PRICE_FULL = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,LTC&tsyms=USD&extraParams=sentpredapp&api_key={0}"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

# Cryptocurrencies' IDs from main_currency table.
cryptocurrency_id_by_ticker = {
    'BTC': 1,
    'ETH': 2,
    'LTC': 3
}
ticker_by_cryptocurrency_id = {
    1: 'BTC',
    2: 'ETH',
    3: 'LTC'
}

# Default values for sentiment, predictions and trends.
DEFAULT_SENT_VALUE = 100.0


class MarketData(object):
    """Reprensetation of main_market table entry."""

    def __init__(self, **params):
        self.date = params.get('date')
        self.globalmarketcap = params.get('globalmarketcap')
        self.mchoursentiment = params.get('mchoursentiment')
        self.mchourprediction = params.get('mchourprediction')
        self.mchourtrend = params.get('mchourtrend')
        self.globalvolume = params.get('globalvolume')

    def jsonify(self):
        return {
            'date': self.date,
            'globalmarketcap': self.globalmarketcap,
            'mchoursentiment': self.mchoursentiment,
            'mchourprediction': self.mchourprediction,
            'mchourtrend': self.mchourtrend,
            'globalvolume': self.globalvolume
        }

    def __repr__(self):
        return "MarketData {0}".format(" ".join(
            [str(self.globalmarketcap), str(self.globalvolume), self.date.strftime("%m/%d/%Y, %H:%M:%S")]))


class PriceData(object):
    """Representation of main_price table entry."""

    def __init__(self, **params):
        self.date = params.get('date')
        self.openprice = params.get('openprice')
        self.highprice = params.get('highprice')
        self.lowprice = params.get('lowprice')
        self.closeprice = params.get('closeprice')
        self.spreadvalue = params.get('spreadvalue')
        self.returnvalue = params.get('returnvalue')
        self.volumeto = params.get('volumeto')
        self.currencyId_id = params.get('currencyId_id')

    def jsonify(self):
        return {
            'date': self.date,
            'openprice': self.openprice,
            'highprice': self.highprice,
            'lowprice': self.lowprice,
            'closeprice': self.closeprice,
            'spreadvalue': self.spreadvalue,
            'returnvalue': self.returnvalue,
            'volumeto': self.volumeto,
            'currencyId_id': self.currencyId_id
        }

    def __repr__(self):
        return "PriceData {0}".format(" ".join(
            [ticker_by_cryptocurrency_id[self.currencyId_id], str(self.closeprice), self.date.strftime("%m/%d/%Y, %H:%M:%S")]))


class MarketDataScraper(object):

    @staticmethod
    def scrape_today_data():
        """Scrape global market data from todays 00:00
        Note, that cmc endpoint requires 1 month date range in order to reply
            with hourly data, not 5min data.
        """
        # Define latest and earliest timestamps for today and required range.
        now = datetime.now()
        today_earliest = datetime(now.year, now.month, now.day)
        today_earliest_unix_ms = int(today_earliest.timestamp() * 1000)
        range_earliest = now - relativedelta(months=1)
        range_earliest_unix_ms = int(range_earliest.timestamp() * 1000)
        range_latest = now + timedelta(hours=1)
        range_latest_unix_ms = int(range_latest.timestamp() * 1000)
        # Build and send request.
        request_url = GLOBAL_MC_VOL.format(range_earliest_unix_ms, range_latest_unix_ms)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_dict = json.loads(response.text)
        # Get today's volume and mktcap values.
        today_mktcap_value = response_dict['market_cap_by_available_supply']
        today_volume_value = response_dict['volume_usd']
        for mktcap_data, vol_data in zip(today_mktcap_value, today_volume_value):
            data_point_timestamp = mktcap_data[0]  # same as vol_data[0]
            if data_point_timestamp >= today_earliest_unix_ms:
                marketdata_obj = MarketData(
                    date=datetime.fromtimestamp(int(mktcap_data[0] / 1000)),
                    globalmarketcap=mktcap_data[1],
                    globalvolume=vol_data[1],
                    mchoursentiment=DEFAULT_SENT_VALUE,
                    mchourprediction=DEFAULT_SENT_VALUE,
                    mchourtrend=DEFAULT_SENT_VALUE
                )
                yield marketdata_obj
        print('Scraped global market data from {0} to {1}\n'.format(
            range_earliest, range_latest))

    @staticmethod
    def scrape_historical_data(from_date, to_date):
        """Scrape historical data about global market by month."""
        # Scrape all the historical data.
        start_range = from_date
        while start_range < to_date:
            # Build request URL
            start_range_unix_ms = int(start_range.timestamp() * 1000)
            end_range = start_range + relativedelta(months=1)
            end_range_unix_ms = int(end_range.timestamp() * 1000)
            request_url = GLOBAL_MC_VOL.format(start_range_unix_ms, end_range_unix_ms)
            # Send a request & collect raw response text
            try:
                response = requests.get(request_url, headers={'User-agent': USER_AGENT})
                response_dict = json.loads(response.text)
            except json.decoder.JSONDecodeError:
                break
            # Yield volume and mktcap data.
            global_mktcap_data = response_dict.get('market_cap_by_available_supply')
            global_volume_data = response_dict.get('volume_usd')
            print('Scraped global market data from {0} to {1}\n'.format(start_range, end_range))
            for mktcap_data, vol_data in zip(global_mktcap_data, global_volume_data):
                marketdata_obj = MarketData(
                    date=datetime.fromtimestamp(int(mktcap_data[0] / 1000)),
                    globalmarketcap=mktcap_data[1],
                    globalvolume=vol_data[1],
                    mchoursentiment=DEFAULT_SENT_VALUE,
                    mchourprediction=DEFAULT_SENT_VALUE,
                    mchourtrend=DEFAULT_SENT_VALUE
                )
                yield marketdata_obj
            # Update start_range with the range end's date.
            start_range = end_range
            # Wait for a bit bc DBAD.
            time.sleep(0.5)


class PriceDataScraper(object):

    def scrape_historical_data(self, ticker, from_date):
        """Get ticker_name historical OHLCVRS data.
        Note, that this method scrapes everything till today's date."""
        # Make first request - the earliest data without toTs parameter.
        request_url = HISTORICAL_PRICE_HOUR.format(ticker, cryptocompare_api_key)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_dict = json.loads(response.text)
        # The earliest dat to compare with in unix format.
        from_date_unixtime = int(from_date.timestamp())
        # Get Price data from the first request.
        first_response_data = response_dict['Data'][::-1]
        print('DBG: Scraped {0} data points from {1} to {2}\n'.format(
            len(first_response_data),
            datetime.fromtimestamp(first_response_data[0]['time']),
            datetime.fromtimestamp(first_response_data[-1]['time'])
        ))
        for item in first_response_data:
            if item['time'] < from_date_unixtime:
                return
            pricedata_to_add = self._cryptocompare_item_to_pricedata(item, ticker)
            yield pricedata_to_add
        # Save toTs value for the next request - the earliest timestamp received from first request.
        toTs = response_dict.get('TimeFrom', None)
        # Scrape historical data depending on tS parameter.
        to_break = False
        while toTs:
            # Make Nth request.
            request_url = HISTORICAL_PRICE_HOUR.format(ticker, cryptocompare_api_key)
            request_url += "&toTs={0}".format(toTs)
            response = requests.get(request_url, headers={'User-agent': USER_AGENT})
            response_dict = json.loads(response.text)
            # Get Price data from the Nth request.
            nth_response_data = response_dict['Data'][:-1][::-1]
            print('DBG: Scraped {0} data points from {1} to {2}\n'.format(
                len(nth_response_data),
                datetime.fromtimestamp(nth_response_data[0]['time']),
                datetime.fromtimestamp(nth_response_data[-1]['time'])
            ))
            for item in nth_response_data:
                # Check if we need any more data from current Nth page.
                if item['time'] < from_date_unixtime:
                    to_break = True
                    break
                pricedata_to_add = self._cryptocompare_item_to_pricedata(item, ticker)
                yield pricedata_to_add
            # Check if we need any more data from any other pages.
            if to_break is True:
                break
            # Update toTs value for the next page.
            toTs = response_dict.get('TimeFrom', None)

    @staticmethod
    def scrape_current_full_data():
        """Get BTC, LTC and ETH current full data, not only OHLCV."""
        # Send a request & collect raw response text
        print('DBG: Trying to get response from requests.get...')
        request_url = CURRENT_PRICE_FULL.format(cryptocompare_api_key)
        response = requests.get(request_url, headers={'User-agent': USER_AGENT})
        response_dict = json.loads(response.text)
        # Get raw data.
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
            currencyId_id=cryptocurrency_id_by_ticker[ticker]
        )
        return price_data


class FinScraperPerformer(object):
    
    def __init__(self):
        # DB connection and cursor instances.
        self.conn = psycopg2.connect()
        self.cur = self.conn.cursor()
        # Existing dates in main_market.
        self.existing_dates_market = self._get_existing_dates_market()
        # Existing dates in main_price.
        self.existing_dates_price = self._get_existing_dates_price()
        # Initialize scrapers.
        self.mds = MarketDataScraper()
        self.pds = PriceDataScraper()
        # The earliest date to scrape.
        self.earliest_date = datetime(2016, 1, 1)

    def scrape_market_data(self):
        # Update existing dates in main_market table.
        raw_existing_dates_market = self._get_existing_dates_market()
        self.existing_dates_market = [(item.date(), item.hour) for item in raw_existing_dates_market]
        # The latest date to scrape.
        latest_date = datetime.now() + timedelta(hours=1)
        # Start scraping market data.
        new_data_container = []
        for mkt_data in self.mds.scrape_historical_data(self.earliest_date, latest_date):
            item_not_in_table_filter = (mkt_data.date.date(), mkt_data.date.hour) not in self.existing_dates_market
            if item_not_in_table_filter:
                new_data_container.append(mkt_data)
                self._save_marketdata(mkt_data)
        return {
            'status': 'OK',
            'data': new_data_container
        }

    def scrape_price_data(self):
        # Update existing dates in main_price table.
        raw_existing_dates_price = self._get_existing_dates_price()
        self.existing_dates_price = [(item.date(), item.hour) for item in raw_existing_dates_price]
        # Start scraping price data by currency ticker.
        new_data_container = []
        for ticker in cryptocurrency_id_by_ticker.keys():
            for price_data in self.pds.scrape_historical_data(ticker, self.earliest_date):
                item_not_in_table_filter = (price_data.date.date(), price_data.date.hour) not in self.existing_dates_price
                if item_not_in_table_filter:
                    new_data_container.append(price_data)
                    self._save_pricedata(price_data)
        return {
            'status': 'OK',
            'data': new_data_container
        }

    def get_last_market_data(self, n_points):
        select_query = """SELECT * FROM main_market ORDER BY date DESC LIMIT %s;"""
        select_query_fields = (n_points, )
        self.cur.execute(select_query, select_query_fields)
        market_data_from_db = self.cur.fetchall()
        market_data = [self._marketdata_jsonify_from_db(row) for row in market_data_from_db]
        return market_data

    def get_last_price_data(self, n_points):
        select_query = """SELECT * FROM main_price ORDER BY date DESC LIMIT %s;"""
        select_query_fields = (n_points, )
        self.cur.execute(select_query, select_query_fields)
        price_data_from_db = self.cur.fetchall()
        price_data = [self._pricedata_jsonify_from_db(row) for row in price_data_from_db]
        return price_data

    @staticmethod
    def _marketdata_jsonify_from_db(row):
        return MarketData(
            date=row[1],
            globalmarketcap=row[2],
            mchoursentiment=row[3],
            mchourprediction=row[4],
            mchourtrend=row[5]
        )

    @staticmethod
    def _pricedata_jsonify_from_db(row):
        return PriceData(
            date=row[1],
            openprice=row[2],
            highprice=row[3],
            lowprice=row[4],
            closeprice=row[5],
            spreadvalue=row[6],
            returnvalue=row[7],
            currencyId_id=row[8],
            volumeto=row[9]
        )

    def _save_marketdata(self, md_obj):
        insert_query = """
            INSERT INTO main_market
            (date, globalmarketcap, mchoursentiment, mchourprediction, mchourtrend, globalvolume)
            VALUES (%s, %s, %s, %s, %s, %s);"""
        insert_query_fields = (
            md_obj.date,
            md_obj.globalmarketcap,
            md_obj.mchoursentiment, md_obj.mchourprediction, md_obj.mchourtrend,
            md_obj.globalvolume
        )
        self.cur.execute(insert_query, insert_query_fields)
        self.conn.commit()
        print('DBG INSERT: inserted {0}'.format(md_obj))

    def _save_pricedata(self, pd_obj):
        insert_query = """
            INSERT INTO main_price
            (date, openprice, highprice, lowprice, closeprice, spreadvalue, returnvalue, "currencyId_id", volumeto)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"""
        insert_query_fields = (
            pd_obj.date,
            pd_obj.openprice, pd_obj.highprice, pd_obj.lowprice, pd_obj.closeprice,
            pd_obj.spreadvalue, pd_obj.returnvalue,
            pd_obj.currencyId_id,
            pd_obj.volumeto
        )
        self.cur.execute(insert_query, insert_query_fields)
        self.conn.commit()
        print('DBG INSERT: inserted {0}'.format(pd_obj))

    def _get_existing_dates_market(self):
        self.cur.execute("""select date from main_market;""")
        existing_dates_fromdb = self.cur.fetchall()
        existing_dates = [row[0] for row in existing_dates_fromdb]
        return existing_dates

    def _get_existing_dates_price(self):
        self.cur.execute("""select date from main_price;""")
        existing_dates_fromdb = self.cur.fetchall()
        existing_dates = [row[0] for row in existing_dates_fromdb]
        return existing_dates


def __dbg():
    from_date = datetime(2018, 1, 1)
    to_date = datetime(2019, 6, 1)

    mdscraper = MarketDataScraper()
    # for mkt_data in mdscraper.scrape_today_data():
    for mkt_data in mdscraper.scrape_historical_data(from_date, to_date):
        print(mkt_data)

    pdscrapper = PriceDataScraper()
    scraped_data = pdscrapper.scrape_current_full_data()
    print(scraped_data)
    for price_data in pdscrapper.scrape_historical_data('ETH', from_date):
        print(price_data)


def __dbg_get():
    fsp = FinScraperPerformer()
    data = fsp.get_last_market_data(20)
    data = fsp.get_last_price_data(20)
    print(data)


def __historical_all_date_range():
    fsp = FinScraperPerformer()
    fsp.scrape_market_data()
    fsp.scrape_price_data()
