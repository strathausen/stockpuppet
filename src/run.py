import sys
from strategy_runner import AlgoTrader

symbol = sys.argv[1]
bar_length = sys.argv[2]
units = float(sys.argv[3])

trader = AlgoTrader("../oanda.cfg", symbol,
                    bar_length=bar_length, window=14, units=units)
trader.start(days=4)
