from strategy_runner import AlgoTrader

trader = AlgoTrader("../oanda.cfg", 'SPX500_USD',
                    bar_length="15min", window=14, units=20)
trader.get_most_recent(days=4)
trader.stream_data(trader.instrument)
