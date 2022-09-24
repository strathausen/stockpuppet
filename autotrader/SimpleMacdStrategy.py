import os
from finta import TA
from autotrader import indicators
from autotrader import Order

from finta import TA
from autotrader import Order, indicators


class SimpleMACD:
    """Simple MACD Strategy

    Rules
    ------
    1. Trade in direction of trend, as per 200EMA.
    2. Entry signal on MACD cross below/above zero line.
    3. Set stop loss at recent price swing.
    4. Target 1.5 take profit.
    """

    def __init__(self, parameters, data, instrument, broker, broker_utils):
        """Define all indicators used in the strategy.
        """
        self.name = "Simple MACD Trend Strategy"
        self.params = parameters
        self.instrument = instrument
        self.broker = broker

        # Initial feature generation (for plotting only)
        self.generate_features(data)

        # Construct indicators dict for plotting
        self.indicators = {
            # 'MACD (12/26/9)': {'type': 'MACD',
            # 'macd': self.MACD.MACD,
            # 'signal': self.MACD.SIGNAL},
            'EMA (slow)': {'type': 'MA', 'data': self.ema_slow},
            'EMA (fast)': {'type': 'MA', 'data': self.ema_fast}
        }

    def generate_features(self, data):
        """Updates MACD indicators and saves them to the class attributes."""
        # Save data for other functions
        self.data = data

        # 200EMA
        self.ema_fast = TA.EMA(self.data, self.params['ema_fast'])
        self.ema_slow = TA.EMA(self.data, self.params['ema_slow'])

        # MACD
        # self.MACD = TA.MACD(self.data, self.params['MACD_fast'],
        # self.params['MACD_slow'], self.params['MACD_smoothing'])
        # self.MACD_CO = indicators.crossover(self.MACD.MACD, self.MACD.SIGNAL)
        # self.MACD_CO_vals = indicators.cross_values(self.MACD.MACD,
        # self.MACD.SIGNAL,
        # self.MACD_CO)

        # Price swings
        self.swings = indicators.find_swings(self.data)

    def generate_signal(self, data):
        """Define strategy to determine entry signals."""

        # if len(self.broker.get_trades()) > 0:
            # return Order()
        # if len(self.broker.get_orders()) > 0:
            # return Order()
        # if len(self.broker.get_positions()) > 0:
            # return Order()
        # Feature calculation
        self.generate_features(data)

        # Downtrend
        # If fast_ema < slow_ema and close < fast_ema and open > fast_ema and no position
        # Go short
        if self.ema_fast[-1] > self.data.Close.values[-1] > self.ema_slow[-1]:
                # self.MACD_CO[-1] == 1 and \
                # self.MACD_CO_vals[-1] < 0:
            # Long entry signal detected! Calculate SL and TP prices
            stop, take = self.generate_exit_levels(signal=1)
            new_order = Order(direction=1, stop_loss=stop, take_profit=take)

        # Uptrend
        # If fast_ema > slow_ema and close > fast_ema and open < fast_ema and no position
        # Go long
        elif self.ema_fast[-1] < self.data.Close.values[-1] < self.ema_fast[-1]:# and \
                # self.MACD_CO[-1] == -1 and \
                # self.MACD_CO_vals[-1] > 0:
            # # Short entry signal detected! Calculate SL and TP prices
            stop, take = self.generate_exit_levels(signal=-1)
            new_order = Order(direction=1, stop_loss=stop, take_profit=take)

        else:
            # No trading signal, return a blank Order
            new_order = Order()

        return new_order

    def generate_exit_levels(self, signal):
        """Function to determine stop loss and take profit prices."""
        RR = self.params['RR']
        if signal == 1:
            # Long signal
            stop = self.swings.Lows[-1]
            take = self.data.Close[-1] + RR*(self.data.Close[-1] - stop)
        else:
            # Short signal
            stop = self.swings.Highs[-1]
            take = self.data.Close[-1] - RR*(stop - self.data.Close[-1])
        return stop, take


keys_config = {
    "OANDA": {
        "LIVE_API": "api-fxtrade.oanda.com",
        "LIVE_ACCESS_TOKEN": "12345678900987654321-abc34135acde13f13530",
        "PRACTICE_API": "api-fxpractice.oanda.com",
        "PRACTICE_ACCESS_TOKEN": "0542437dd6b0c23b6fddf6d7c365a740-479f83263cee291d2787d1192d9a262c",
        # "PRACTICE_ACCESS_TOKEN": "56a9ff8f6efb7801d70ffa92a8ae0f87-ed6f74770010fc9b6e5effc9a15f2b79",
        "DEFAULT_ACCOUNT_ID": "101-012-22532260-001",
        "PORT": 443,
    },
}

data_config = {
    'data_source': "oanda",
    'API': "api-fxpractice.oanda.com",
    'ACCESS_TOKEN': keys_config['OANDA']['PRACTICE_ACCESS_TOKEN'],
    'PORT': 443,
    'ACCOUNT_ID': keys_config['OANDA']['DEFAULT_ACCOUNT_ID'],
}

if __name__ == "__main__":
    from autotrader import AutoTrader, AutoData
    # at = AutoTrader()
    # at.configure(show_plot=True, verbosity=1, feed='yahoo',
                # mode='continuous', update_interval='5min') 
    # at.add_strategy('macd') 
    # at.backtest(start = '19/9/2022', end = '23/9/2022')
    # at.virtual_account_config(leverage=20)
    # at.run()


    ad = AutoData(data_config)
    config = {'NAME': 'MACD Strategy',
              'MODULE': 'macd_strategy',
              'CLASS': 'SimpleMACD',
              'INTERVAL': '5min',
              'PERIOD': 300,
              'RISK_PC': 1,
              'SIZING': 'risk',
              'INCLUDE_BROKER': True,
              'PARAMETERS': {'ema_slow': 46,
                             'ema_fast': 9,
                             'RR': 1.5},
              'WATCHLIST': ['SPX500_USD'], }

    at = AutoTrader()
    at.configure(verbosity=1, show_plot=False, feed='yahoo', broker="virtual",
                 global_config=keys_config, mode='continuous')
    # at.configure(verbosity=1, show_plot=False, feed='oanda',
                 # broker='oanda', global_config=keys_config, mode='continuous')
    # at.add_strategy(config_dict=config, strategy=SimpleMACD)
    at.plot_settings(show_cancelled=False)
    # at.add_data({'EUR_USD': 'EUR_USD_H4.csv'},
    # data_directory=os.path.join(os.getcwd(), 'data'))
    at.virtual_account_config(
        leverage=20, initial_balance=100000)
    at.backtest(start='20/9/2022', end='23/9/2022')
    # initial_balance=1000,
    # leverage=30,
    # spread=0.5,
    # commission=0.005)
    at.run()
