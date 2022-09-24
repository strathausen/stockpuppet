import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import List
from create_features import create_features
from os.path import exists, dirname
import tpqoa
from DNNModel import *
import pickle

oanda = tpqoa.tpqoa('../oanda.cfg')

plt.style.use("seaborn")
pd.set_option('display.float_format', lambda x: '%.5f' % x)


class DnnStrategy:
    # Trading history and indicators
    raw_data: pd.DataFrame
    # Data with features and lags
    data: pd.DataFrame
    # Slice of data for the training set
    train: pd.DataFrame
    # Slice of data for the outsample testing
    test: pd.DataFrame

    # How much of the data will be used for training
    split_ratio = 0.66

    # Feaures that are being used for training and predicting
    cols: List[str] = []
    # Feaures without lags, for debugging
    features: List[str] = []

    # Cost for transactions
    ptc = 0.000059

    # Used for downloading trading data as csv
    interval = 'M15'
    start = '01-01-2020'
    end = '01-01-2021'

    oanda = oanda

    def __init__(self, instrument: str, window=14, lags=10, interval='M15'):
        self.instrument = instrument
        self.window = window
        self.lags = lags
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
        self.cols, self.features, self.data = create_features(
            self.raw_data, self.window, self.lags)

    def plot_features(self):
        # debug_cols = self.features + ['Close']
        self.data[self.features].plot(fontsize=12, figsize=(20, 12))
        plt.legend(fontsize=16)
        plt.show()

    def train_and_save(self):
        """Trains on the data and saves the model + parameters"""
        df = self.data
        cols = self.cols
        split = int(len(df) * self.split_ratio)
        train = df.iloc[:split].copy()
        self.train = train
        test = df.iloc[split:].copy()
        self.test = test

        # Feature scaling (Standardization)
        mu, std = train.mean(), train.std()
        train_s = (train - mu) / std

        # fitting a DNN model with 3 Hidden Layers (50 nodes each) and dropout
        # regularization
        set_seeds(100)
        model = create_model(hl=3, hu=60, dropout=True,
                             input_dim=len(cols))
        model.fit(x=train_s[cols], y=train["dir"], epochs=60,
                  verbose=False, validation_split=0.2, shuffle=False,
                  class_weight=cw(train))
        model.evaluate(train_s[cols], train["dir"])
        pred = model.predict(train_s[cols])
        # print(pred)
        self.pred = pred

        # standardization of test set features (with train set parameters!!!)
        test_s = (test - mu) / std
        model.evaluate(test_s[cols], test["dir"])
        # Only test during NY stock marked open hours
        test.index = test.index.tz_localize("UTC")
        test["NYTime"] = test.index.tz_convert("America/New_York")
        test["hour"] = test.NYTime.dt.hour
        # pred = model.predict(test_s[cols])
        test["proba"] = model.predict(test_s[cols])
        # 1. short where proba < 0.47
        test["position"] = np.where(test.proba < 0.47, -1, np.nan)
        # 2. long where proba > 0.53
        test["position"] = np.where(test.proba > 0.53, 1, test.position)
        # 3. neutral in non-busy hours
        test["position"] = np.where(
            ~test.hour.between(2, 12), 0, test.position)
        # 4. in all other cases: hold position
        test["position"] = test.position.ffill().fillna(0)

        test["trades"] = test.position.diff().abs()
        print(test.position.value_counts(dropna = False))
        self.calculate_returns(test)
        model.save(f"{self.prefix()}_DNN_model")
        params = {"mu": mu, "std": std,
                  "window": self.window, "lags": self.lags}
        pickle.dump(params, open(f"{self.prefix()}_params.pkl", "wb"))

        self.test = test

    def macdh_strategy(self):
        test = self.data
        # Only test during NY stock marked open hours
        test.index = test.index.tz_localize("UTC")
        test["NYTime"] = test.index.tz_convert("America/New_York")
        test["hour"] = test.NYTime.dt.hour
        test["position"] = test.macdh_strat.shift()
        # 3. neutral in non-busy hours
        test["position"] = np.where(
            ~test.hour.between(2, 12), 0, test.position)
        # 4. in all other cases: hold position
        test["position"] = test.position.ffill().fillna(0)

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
        self.test[["creturns", "cstrategy", "cstrategy_net"]].plot(
            figsize=(20, 12))
        plt.show()
