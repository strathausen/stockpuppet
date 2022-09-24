from pandas import DataFrame
import pandas_ta
from typing import List
import numpy as np


def create_features(data: DataFrame, window: int, lags: int):
    col = 'close'
    data["returns"] = np.log(data[col] / data[col].shift())
    df = data.copy()
    df["dir"] = np.where(df["returns"] > 0, 1, 0)
    # df["sma"] = df[col].rolling(
        # window).mean() - df[col].rolling(20).mean()
    df["ema_fast"] = df[col].ewm(span=12, min_periods=12).mean()
    df["ema_12"] = df[col].ewm(span=12, min_periods=12).mean()
    df["ema_26"] = df[col].ewm(span=26, min_periods=26).mean()
    df["ema_slow"] = df[col].ewm(span=150, min_periods=150).mean()
    # df["ema_100"] = df[col].ewm(span=100, min_periods=100).mean()
    df["ema_strategy"] = df["ema_26"] - df["ema_12"]
    df["boll"] = (df[col] - df[col].rolling(window).mean()) / \
        df[col].rolling(window).std()
    df["min"] = df[col].rolling(window).min() / df[col] - 1
    df["max"] = df[col].rolling(window).max() / df[col] - 1
    df["mom"] = df["returns"].rolling(4).mean()
    df["vol"] = df["returns"].rolling(window).std()
    df.ta.macd(close='close', fast=12, slow=26, append=True)
    df.columns = [x.lower() for x in df.columns]
    df['rsi'] = df.ta.rsi(close='close')
    # df['rsi_upper'] = df['rsi'] - 30
    # df['rsi_lower'] = df['rsi'] - 70
    df['rsi_strategy'] = (df['rsi'] - 50) / 100

    macdh_cur = df['macdh_12_26_9']#.shift()
    macdh_mid = macdh_cur.shift()
    macdh_prv = macdh_mid.shift()
    df['macdh_strat'] = np.where((macdh_prv < macdh_mid) & (
        macdh_mid > macdh_cur) & (macdh_mid > 0) & (df['ema_strategy'] > 0) & (df['rsi_strategy'] < -0.0) & (df[col] < df['ema_slow']), -1, np.nan)
    df['macdh_strat'] = np.where((macdh_prv > macdh_mid) & (
        macdh_mid < macdh_cur) & (macdh_mid < 0) & (df['ema_strategy'] < 0) & (df['rsi_strategy'] > +0.0) & (df[col] > df['ema_slow']), 1, df['macdh_strat'])
    df['signals'] = df['macdh_strat']
    df['exit_long'] = np.where(df[col] < df['ema_fast'], True, False)
    df['exit_short'] = np.where(df[col] > df['ema_fast'], True, False)
    # df['signals'].fillna(0)
    # df["macdh_strat"] = df['macdh_strat'].ffill().fillna(0)
    # df['macdh_strat'] = df['macdh_strat'].shift().dropna()

    # df.dropna(inplace=True)
    # Adding feature lags
    features = ["dir", 'mom', 'vol', 'boll', 'macdh_strat']
    cols: List[str] = []
    for f in features:
        for lag in range(1, lags + 1):
            col = f"{f}_lag_{lag}"
            df[col] = df[f].shift(lag)
            cols.append(col)

    # df.dropna(inplace=True)
    return cols, features, df
