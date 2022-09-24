import keras
import pandas as pd
import numpy as np
import tpqoa
from datetime import datetime, timedelta
import time
import os
import pickle

from create_features import create_features

os.environ['F_ENABLE_ONEDNN_OPTS'] = '0'
# Loading the model


class DNNTrader():
    data: pd.DataFrame
    raw_data: pd.DataFrame
    last_bar: int
    oanda: tpqoa.tpqoa

    def __init__(self, conf_file: str, instrument: str, bar_length: str, window: int, lags: int, model, mu: float, std: float, units: int):
        self.oanda = tpqoa.tpqoa(conf_file)
        self.instrument = instrument
        self.bar_length = pd.to_timedelta(bar_length)
        self.tick_data = pd.DataFrame()
        self.units = units
        self.position = 0
        self.profits = []

        # *****************add strategy-specific attributes here******************
        self.window = window
        self.lags = lags
        self.model = model
        self.mu = mu
        self.std = std
        # ************************************************************************

    def get_most_recent(self, days=14):
        while True:
            time.sleep(2)
            now = datetime.utcnow()
            now = now - timedelta(microseconds=now.microsecond)
            past = now - timedelta(days=days)
            df: pd.DataFrame = self.oanda.get_history(instrument=self.instrument, start=past, end=now,
                                                      granularity="S5", price="M", localize=False).c.dropna().to_frame()
            df.rename(columns={"c": 'Close'}, inplace=True)
            df = df.resample(
                self.bar_length, label="right").last().dropna().iloc[:-1]
            self.raw_data = df.copy()
            self.last_bar = self.raw_data.index[-1]
            if pd.to_datetime(datetime.utcnow()).tz_localize("UTC") - self.last_bar < self.bar_length:
                self.start_time = pd.to_datetime(datetime.utcnow()).tz_localize(
                    "UTC")  # NEW -> Start Time of Trading Session
                break

    def on_success(self, time, bid, ask):
        print(self.oanda.ticks, end=" ", flush=True)

        recent_tick = pd.to_datetime(time)
        df = pd.DataFrame({self.instrument: (ask + bid)/2},
                          index=[recent_tick])
        self.tick_data = self.tick_data.append(df)

        if recent_tick - self.last_bar > self.bar_length:
            self.resample_and_join()
            self.define_strategy()
            self.execute_trades()

    def resample_and_join(self):
        self.raw_data = self.raw_data.append(self.tick_data.resample(self.bar_length,
                                                                     label="right").last().ffill().iloc[:-1])
        self.tick_data = self.tick_data.iloc[-1:]
        self.last_bar = self.raw_data.index[-1]

    def define_strategy(self):  # "strategy-specific"
        df = self.raw_data.copy()
        # append latest tick (== open price of current bar)
        df = df.append(self.tick_data)

        cols, features, df = create_features(df, self.window, self.lags)

        self.cols = cols

        # ******************** define your strategy here ************************

        # standardization
        df_s = (df - self.mu) / self.std
        # predict probability
        df["proba"] = self.model.predict(df_s[self.cols])

        # determine positions
        # starting with first live_stream bar (removing historical bars)
        df = df.loc[self.start_time:].copy()
        df["position"] = np.where(df.proba < 0.47, -1, np.nan)
        df["position"] = np.where(df.proba > 0.53, 1, df.position)
        # start with neutral position if no strong signal
        df["position"] = df.position.ffill().fillna(0)
        # ***********************************************************************

        self.data = df.copy()

    def execute_trades(self):
        if self.data["position"].iloc[-1] == 1:
            if self.position == 0:
                order = self.oanda.create_order(
                    self.instrument, self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING LONG")
            elif self.position == -1:
                order = self.oanda.create_order(
                    self.instrument, self.units * 2, suppress=True, ret=True)
                self.report_trade(order, "GOING LONG")
            self.position = 1
        elif self.data["position"].iloc[-1] == -1:
            if self.position == 0:
                order = self.oanda.create_order(
                    self.instrument, -self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING SHORT")
            elif self.position == 1:
                order = self.oanda.create_order(
                    self.instrument, -self.units * 2, suppress=True, ret=True)
                self.report_trade(order, "GOING SHORT")
            self.position = -1
        elif self.data["position"].iloc[-1] == 0:
            if self.position == -1:
                order = self.oanda.create_order(
                    self.instrument, self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING NEUTRAL")
            elif self.position == 1:
                order = self.oanda.create_order(
                    self.instrument, -self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING NEUTRAL")
            self.position = 0

    def report_trade(self, order, going):
        time = order["time"]
        units = order["units"]
        price = order["price"]
        pl = float(order["pl"])
        self.profits.append(pl)
        cumpl = sum(self.profits)
        print("\n" + 100 * "-")
        print("{} | {}".format(time, going))
        print("{} | units = {} | price = {} | P&L = {} | Cum P&L = {}".format(
            time, units, price, pl, cumpl))
        print(100 * "-" + "\n")
        # TODO insert into postgres database here


def run(symbol: str):
    model = keras.models.load_model(f"DNN_model_{symbol}")
    params = pickle.load(open(f"params_{symbol}.pkl", "rb"))
    mu = params["mu"]
    std = params["std"]
    lags = params['lags']
    window = params['window']
    trader = DNNTrader("oanda.cfg", "EUR_USD", bar_length="20min",
                       window=window, lags=lags, model=model, mu=mu, std=std, units=100000)
    trader.get_most_recent()
