from autotrader import AutoTrader, AutoData

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

ad = AutoData(data_config)
at = AutoTrader()
at.configure(show_plot=True, verbosity=1, feed='oanda', broker='oanda',
             mode='continuous', update_interval='5min', global_config=keys_config) 
at.add_strategy('macd') 
at.backtest(start = '14/7/2022', end = '7/9/2022')
at.virtual_account_config(leverage=20)
at.run()
