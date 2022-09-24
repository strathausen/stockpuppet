import pandas as pd
import numpy as np
import tpqoa
from datetime import datetime, timedelta
import time

from create_features import create_features


class AlgoTrader(tpqoa.tpqoa):
    data: pd.DataFrame
    raw_data: pd.DataFrame
    last_bar: int
    duration = 8.5 * 60 * 60  # 8.5h

    def __init__(self, conf_file: str, instrument: str, bar_length: str, window: int, units: float):
        super().__init__(conf_file)
        self.instrument = instrument
        self.bar_length = pd.to_timedelta(bar_length)
        self.tick_data = pd.DataFrame()
        self.units = units
        self.position = 0
        self.profits = []
        self.start_ts = time.time()

        # ****************add strategy-specific attributes here******************
        self.window = window
        # ***********************************************************************

    def get_most_recent(self, days=14):
        while True:
            time.sleep(2)
            now = datetime.utcnow()
            now = now - timedelta(microseconds=now.microsecond)
            past = now - timedelta(days=days)
            df: pd.DataFrame = self.get_history(instrument=self.instrument, start=past, end=now,
                                                granularity="S5", price="M", localize=False).c.dropna().to_frame()
            df.rename(columns={"c": 'close'}, inplace=True)
            df = df.resample(
                self.bar_length, label="right").last().dropna().iloc[:-1]
            self.raw_data = df.copy()
            self.last_bar = self.raw_data.index[-1]
            if pd.to_datetime(datetime.utcnow()).tz_localize("UTC") - self.last_bar < self.bar_length:
                self.start_time = pd.to_datetime(datetime.utcnow()).tz_localize(
                    "UTC")  # NEW -> Start Time of Trading Session
                break

    def on_success(self, timestamp, bid, ask):
        print(self.ticks, end='\r', flush=True)
        recent_tick = pd.to_datetime(timestamp)
        df = pd.DataFrame({'close': (ask + bid)/2}, index=[recent_tick])
        self.tick_data = pd.concat([self.tick_data, df])

        # if a time longer than the bar_lenght has elapsed between last full bar and the most recent tick
        if recent_tick - self.last_bar > self.bar_length:
            self.resample_and_join()
            self.define_strategy()
            self.execute_trades()
        # Stop after duration
        if time.time() - self.start_ts > self.duration:
            self.stop()

    def resample_and_join(self):
        self.raw_data = pd.concat([self.raw_data, self.tick_data.resample(
            self.bar_length, label="right").last().ffill().iloc[:-1]])
        self.tick_data = self.tick_data.iloc[-1:]
        self.last_bar = self.raw_data.index[-1]

    def define_strategy(self):  # "strategy-specific"
        df = self.raw_data.copy()
        # append latest tick (== open price of current bar)
        df = pd.concat([df, self.tick_data])

        cols, features, df = create_features(df, self.window, 0)

        # ******************** define your strategy here ************************

        # standardization
        df = df.loc[self.start_time:].copy()
        # df["position"] = df.macdh_strat
        # start with neutral position if no strong signal
        df["position"] = df.signals.ffill().fillna(0)
        # ***********************************************************************

        self.data = df.copy()

    def execute_trades(self):
        if len(self.data['position']) == 0:
            print('pos len 0')
            return
        if self.data["position"].iloc[-1] == 1:
            if self.position == 0:
                order = self.create_order(
                    self.instrument, self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING LONG")
            elif self.position == -1:
                order = self.create_order(
                    self.instrument, self.units * 2, suppress=True, ret=True)
                self.report_trade(order, "GOING LONG")
            self.position = 1
        elif self.data["position"].iloc[-1] == -1:
            if self.position == 0:
                order = self.create_order(
                    self.instrument, -self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING SHORT")
            elif self.position == 1:
                order = self.create_order(
                    self.instrument, -self.units * 2, suppress=True, ret=True)
                self.report_trade(order, "GOING SHORT")
            self.position = -1
        elif self.data["position"].iloc[-1] == 0:
            if self.position == -1:
                order = self.create_order(
                    self.instrument, self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING NEUTRAL")
            elif self.position == 1:
                order = self.create_order(
                    self.instrument, -self.units, suppress=True, ret=True)
                self.report_trade(order, "GOING NEUTRAL")
            self.position = 0
        else:
            print('doing nothing')

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

    def stop(self):
        self.stop_stream = True
        if self.position != 0:
            self.close_orders()
        print('stopped trading')

    def close_orders(self):
        close_order = self.create_order(self.instrument, units=-self.position * self.units,
                                        suppress=True, ret=True)
        self.report_trade(close_order, "GOING NEUTRAL")
        self.position = 0

    def start(self, days=4):
        self.get_most_recent(days=days)
        while True:
            try:
                self.stream_data(self.instrument)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                print(e)
                time.sleep(2)
