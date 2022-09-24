from pandas import DataFrame
import pandas_ta as ta
import numpy as np


def create_features(data: DataFrame):
    col = 'close'
    window = 5
    ema_rsi = 12
    ema_fast = 9
    ema_slow = 50
    data["returns"] = np.log(data[col] / data[col].shift())
    df = data.copy()
    df["mom"] = df["returns"].rolling(4).mean()
    df["vol"] = df["returns"].rolling(window).std()
    df['rsi'] = df.ta.rsi(close='close')
    df['rsi_ema'] = df['rsi'].ewm(span=ema_rsi, min_periods=ema_rsi).mean()
    ###
    # Downtrend:
    # if slow > close > fast
    # then
    #    go short! until price touches fast ema
    #
    # Uptrend:
    # if slow < close < fast
    # then
    #    go long! until price touches fast ema
    ###

    df["ema_fast"] = df[col].ewm(span=ema_fast, min_periods=ema_fast).mean()
    df["ema_slow"] = df[col].ewm(span=ema_slow, min_periods=ema_slow).mean()
    # & (df['rsi_ema'] < df['rsi'])
    # LONG
    df['signals'] = np.where((df['ema_slow'] < df[col]) & (df[col] < df['ema_fast']), -1, np.nan)
    # SHORT
    df['signals'] = np.where((df['ema_slow'] > df[col]) & (df[col] > df['ema_fast']), 1, df['signals'])
    df['signals'].fillna(0, inplace=True)
    # df['signals'] = df['signals'].shift()
    # df = df.dropna()

    features = ['ema_slow', 'ema_fast', col]

    return df, features
