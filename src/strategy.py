import matplotlib.pyplot as plt
import time
import numpy as np
import pandas as pd
from typing import List
from create_features_algo import create_features
from os.path import exists, dirname
import tpqoa

oanda = tpqoa.tpqoa('../oanda.cfg')

plt.style.use("seaborn")
pd.set_option('display.float_format', lambda x: '%.5f' % x)


class AlgoStrategy:
    # Trading history and indicators
    raw_data: pd.DataFrame
    # Data with features
    data: pd.DataFrame
    # Run strategy tests on the data
    test: pd.DataFrame

    # Cost for transactions
    ptc = 0.000059

    # Used for downloading trading data as csv
    interval = 'M5'
    start = '2022-01-01'
    end = '2022-20-09'
    duration = 8.5 * 60 * 60  # 8.5h

    oanda = oanda

    def __init__(self, instrument: str, window=14, interval='M15'):
        self.instrument = instrument
        self.window = window
        self.interval = interval

    def prefix(self):
        file_path = dirname(__file__)
        return f"{file_path}/../data/{self.instrument}_{self.interval}_{self.start}_{self.end}"

    def download_data(self):
        file_name = f"{self.prefix()}.csv"
        if exists(file_name):
            self.raw_data: pd.DataFrame = pd.read_csv(
                file_name, header=[0], index_col=[0], parse_dates=[0])
        else:
            # self.raw_data = yf.download(
            # self.instrument, start='2022-05-01', end='2022-07-27')
            self.raw_data: pd.DataFrame = oanda.get_history(
                instrument=self.instrument,
                granularity=self.interval,
                price='M',
                start=self.start,
                end=self.end
            )
            self.raw_data.rename(
                columns={'c': 'close', 'h': 'high', 'l': 'low', 'o': 'open'}, inplace=True)
            self.raw_data.columns = [x.lower() for x in self.raw_data.columns]
            self.raw_data.index.names = ['datetime']
            self.raw_data.to_csv(file_name)

    def add_features(self):
        self.data, self.features = create_features(self.raw_data)

    def plot_features(self):
        # debug_cols = self.features + ['Close']
        self.data[self.features].plot(fontsize=12, figsize=(20, 12))
        plt.legend(fontsize=16)
        plt.show()

    def macdh_strategy(self):
        test = self.data
        # Only test during NY stock marked open hours
        test.index = test.index.tz_localize("UTC")
        test["NYTime"] = test.index.tz_convert("America/New_York")
        test["hour"] = test.NYTime.dt.hour
        test["position"] = test.signals#.shift()
        # 3. neutral in non-busy hours
        test["position"] = np.where(
            ~test.hour.between(2, 12), 0, test.position)
        # 4. in all other cases: hold position
        #test["position"] = test.position.ffill().fillna(0)
        # test['position'] = np.where((test['position'] == 1) & (test['exit_long'].shift()), 0, test['position'])
        # test['position'] = np.where((test['position'] == -1) & (test['exit_short'].shift()), 0, test['position'])

        test["trades"] = test.position.diff().abs()
        self.test = test
        self.calculate_returns(test)
    
    def calculate_returns(self, test: pd.DataFrame):
        test["strategy"] = test["position"] * test["returns"]
        test["creturns"] = test["returns"].cumsum().apply(np.exp)
        test["cstrategy"] = test["strategy"].cumsum().apply(np.exp)
        test["strategy_net"] = test.strategy - test.trades * self.ptc
        test["cstrategy_net"] = test["strategy_net"].cumsum().apply(np.exp)

    # TODO https://www.alpharithms.com/calculate-macd-python-272222/
    def plot_test(self):
        self.test[["creturns", "cstrategy", "cstrategy_net"]].plot(figsize=(20, 12))
        plt.show()
