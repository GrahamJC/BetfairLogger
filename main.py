import betfairlightweight
import pprint

AppKey = 'V21Qsfs6cp7LSSXO'
Username = 'graham.cockell@outlook.com'
Password = 'd57j*PZk'

trading = betfairlightweight.APIClient(Username, Password, app_key=AppKey, cert_files=['./certs/client-2048.crt', './certs/client-2048.key'])
trading.login()
print(trading.betting.list_event_types())