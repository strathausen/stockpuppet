import os
os.environ['F_ENABLE_ONEDNN_OPTS'] = '0'
import matplotlib
matplotlib.use('module://matplotlib-backend-kitty')
import matplotlib.pyplot as plt
import strategy

inst = strategy.AlgoStrategy('US30_USD')
inst.start = '2022-06-01'
inst.end = '2022-06-15'
inst.interval = 'S5'
# inst = strategy.AlgoStrategy('SPX500_USD')
inst.download_data()
inst.add_features()
# inst.train_and_save()
inst.macdh_strategy()
inst.plot_test()

# import tpqoa
# api = tpqoa.tpqoa("oanda.cfg")
# print('\n'.join([f"{i} - {a}" for i, a in api.get_instruments()]))
# api.get_history('EUR_USD', '2020-01-20', '2020-01-21', 'D', 'M', localize=False)
# data = api.get_history(instrument='EUR_USD',
# start='2022-05-01',
# end='2022-07-30',
# granularity='H1',
# price='M')

# print(data)
