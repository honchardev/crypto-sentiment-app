import warnings
from datetime import datetime, timedelta

import pandas as pd
import psycopg2


class MarketDataCleaner(object):
    """Get data from main_market table and preprocess it into pandas.Dataframe"""

    def __init__(self):
        # DB connection and cursor instances.
        self.conn = psycopg2.connect()

    def clean(self):
        # Load all rows from the main_price.
        market_df = self._get_df()
        # Convert all the datetimes to UTC time zone.
        market_df['date'] = pd.to_datetime(market_df['date'], utc=True)
        # Add day and hour columns for better work with date.
        market_df['daycol'] = market_df['date'].dt.date
        market_df['hourcol'] = market_df['date'].dt.hour
        # Remove data points which share the same date&hour.
        print('Start removing data points with same date and hour')
        ids_to_drop = []
        grouped_by_dayhour = market_df.groupby(['daycol', 'hourcol'])
        for _, df in grouped_by_dayhour:
            if df.shape[0] != 1:
                for value in df.index.values[1:]:
                    ids_to_drop.append(value)
        market_df = market_df.drop(ids_to_drop)
        # Check if there are Null values.
        print('There are {0} NA values main_market'.format(
            market_df.isnull().sum().sum()))
        # Compare with real hourly data points - fill missing values.
        cur_date = datetime.now()
        finish_date = datetime(2016, 1, 1)
        hour_timedelta = timedelta(hours=1)
        while cur_date > finish_date:
            filter_day = market_df['daycol'] == cur_date.date()
            filter_hour = market_df['hourcol'] == cur_date.hour
            if market_df[filter_day & filter_hour].empty:
                print(
                    'Found empty value from market_data at {0}'.format(cur_date))
                df_to_add_data = {
                    'date': [cur_date],
                    'globalmarketcap': [market_df[filter_day].mean()['globalmarketcap']],
                    'mchoursentiment': [market_df[filter_day].mean()['mchoursentiment']],
                    'mchourprediction': [market_df[filter_day].mean()['mchourprediction']],
                    'mchourtrend': [market_df[filter_day].mean()['mchourtrend']],
                    'globalvolume': [market_df[filter_day].mean()['globalvolume']],
                    'daycol': [cur_date.date()],
                    'hourcol': [cur_date.hour]
                }
                df_to_add = pd.DataFrame(df_to_add_data)
                market_df.append(df_to_add, ignore_index=True)
            cur_date -= hour_timedelta
        # Return cleaned data.
        return market_df

    def _get_df(self):
        select_query = """select * from main_market;"""
        data_df = pd.read_sql_query(select_query, self.conn, index_col='id')
        return data_df


class PriceDataCleaner(object):
    """Get data from main_market table and preprocess it into pandas.Dataframe"""

    def __init__(self):
        # DB connection and cursor instances.
        self.conn = psycopg2.connect(
            user="sentimentappadmin", password="pass",  host="127.0.0.1", database="sentimentappdb")

    def clean(self):
        # Load all rows from the main_price.
        prices_df = self._get_df()
        # Convert all the datetimes to UTC time zone.
        prices_df['date'] = pd.to_datetime(prices_df['date'], utc=True)
        # Add day and hour columns for better work with date.
        prices_df['daycol'] = prices_df['date'].dt.date
        prices_df['hourcol'] = prices_df['date'].dt.hour
        # Separate BTC, ETH and LTC price entries.
        cryptocurrency_id_by_ticker = {
            'BTC': 1,
            'ETH': 2,
            'LTC': 3
        }
        prices_by_ticker = {
            key: prices_df[prices_df['currencyId_id'] == val]
            for key, val in cryptocurrency_id_by_ticker.items()
        }
        # Remove data points which share the same date&hour.
        prices_by_ticker_singular = {}
        for ticker, ticker_df in prices_by_ticker.items():
            print('Removing duplicated hours from {0} ticker'.format(ticker))
            # Container to save duplicated IDs to remove.
            ids_to_drop = []
            # Ticker data to work with.
            ticker_df_to_add = ticker_df.loc[:, :]
            # Group by day & hour.
            grouped = ticker_df_to_add.groupby(['daycol', 'hourcol'])
            # Get ids to drop.
            for key, df in grouped:
                if df.shape[0] != 1:
                    for value in df.index.values[1:]:
                        ids_to_drop.append(value)
            # Drop selected ids.
            ticker_df_to_add = ticker_df_to_add.drop(ids_to_drop)
            # Save prices_df by ticker without duplicated IDs.
            prices_by_ticker_singular[ticker] = ticker_df_to_add
        # Check if there is any NA values.
        for key in prices_by_ticker_singular.keys():
            print('There are {0} NA values in {1} df'.format(
                prices_by_ticker_singular[key].isnull().sum().sum(), key))
        # Compare with real hourly data points - fill missing values.
        print('Comparing with real hourly data points and filling missing values.')
        cleaned_data = {}
        for ticker, ticker_df in prices_by_ticker_singular.items():
            # Ticker data to work with.
            ticker_to_work_df = ticker_df.loc[:, :]
            # Dates to go through.
            cur_date = datetime.now()
            finish_date = datetime(2016, 1, 1)
            hour_timedelta = timedelta(hours=1)
            print('Start checking {0} ticker for missing data.'.format(ticker))
            # Check if there is data for every hour in a date range.
            while cur_date > finish_date:
                filter_day = ticker_to_work_df['daycol'] == cur_date.date()
                filter_hour = ticker_to_work_df['hourcol'] == cur_date.hour
                if ticker_to_work_df[filter_day & filter_hour].empty:
                    print('Found missing value from market_price of {0} at {1}'.format(
                        ticker, cur_date))
                    df_to_add_data = {
                        'date': [cur_date],
                        'openprice': [ticker_to_work_df[filter_day].mean()['openprice']],
                        'highprice': [ticker_to_work_df[filter_day].mean()['highprice']],
                        'lowprice': [ticker_to_work_df[filter_day].mean()['lowprice']],
                        'closeprice': [ticker_to_work_df[filter_day].mean()['closeprice']],
                        'currencyId_id': [cryptocurrency_id_by_ticker[ticker]],
                        'volumeto': [ticker_to_work_df[filter_day].mean()['volumeto']],
                        'daycol': [cur_date.date()],
                        'hourcol': [cur_date.hour]
                    }
                    df_to_add_data['spreadvalue'] = [
                        df_to_add_data['highprice'][0] - df_to_add_data['lowprice'][0]]
                    df_to_add_data['returnvalue'] = [
                        df_to_add_data['openprice'][0] - df_to_add_data['closeprice'][0]]
                    df_to_add = pd.DataFrame(df_to_add_data)
                    ticker_to_work_df.append(df_to_add, ignore_index=True)
                cur_date -= hour_timedelta
            # Save cleaned ticker data.
            cleaned_data[ticker] = ticker_to_work_df
        # Return cleaned data.
        return cleaned_data

    def _get_df(self):
        select_query = """select * from main_price;"""
        data_df = pd.read_sql_query(select_query, self.conn, index_col='id')
        return data_df


def __dbg():
    warnings.filterwarnings('ignore')

    pdc = PriceDataCleaner()
    pdc.clean()

    mdc = MarketDataCleaner()
    mdc.clean()

    print('end of the program')
