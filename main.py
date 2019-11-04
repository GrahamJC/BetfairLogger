import betfairlightweight
import json

with open('secrets.json') as f:
    secrets = json.loads(f.read())

trading = betfairlightweight.APIClient(secrets['username'], secrets['password'], app_key=secrets['app_key'], cert_files=['./certs/client-2048.crt', './certs/client-2048.key'])
trading.login()
print(trading.betting.list_event_types())