from strategy_runner import AlgoTrader

trader = AlgoTrader("../oanda.cfg", 'UK100_GBP',
                    bar_length="15min", window=14, units=1)
trader.get_most_recent(days=2)
trader.stream_data(trader.instrument)
