import datetime
import json
from time import sleep
import traceback

import sqlalchemy as sql

import betfairlightweight as bfl

from models import Event, Runner, Jockey, Trainer, Market, MarketRunner, MarketBook, MarketRunnerBook, MarketRunnerOrder

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@192.168.1.1:32768/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@localhost/betfairlogger'


def get_metadata(db_session, betfair_api, event):

    bfl_markets = betfair_api.betting.list_market_catalogue(
        filter = bfl.filters.market_filter(
            event_ids = [event.betfair_id],
        ),
        max_results=25,
        market_projection=['RUNNER_METADATA']
    )
    for bfl_market in bfl_markets:
        market = db_session.query(Market).filter(Market.event_id == event.id, Market.betfair_id == bfl_market.market_id).one_or_none()
        if market:
            print(f"  Market: {market.name}")
            for bfl_runner in bfl_market.runners:
                runner = db_session.query(Runner).filter(Runner.betfair_id == bfl_runner.selection_id).one_or_none()
                if runner:
                    print(f"    Runner: {runner.name}")
                    print(f"      Jockey: {bfl_runner.metadata['JOCKEY_NAME']}")
                    print(f"      Trainer: {bfl_runner.metadata['TRAINER_NAME']}")
                    market_runner = None #db_session.query(MarketRunner).filter(MarketRunner.market_id == market.id, MarketRunner.runner_id == runner.id).one_or_none()
                    if  market_runner:
                        jockey_name = bfl_runner.metadata['JOCKEY_NAME']
                        if jockey_name:
                            jockey = db_session.query(Jockey).filter(Jockey.name == jockey_name).one_or_none()
                            if not jockey:
                                jockey = Jockey(
                                    name = jockey_name,
                                )
                                db_session.add(jockey)
                            market_runner.jockey_id = jockey.id
                        trainer_name = bfl_runner.metadata['TRAINER_NAME']
                        if trainer_name:
                            trainer = db_session.query(Trainer).filter(Trainer.name == trainer_name).one_or_none()
                            if not trainer:
                                trainer = Trainer(
                                    name = trainer_name,
                                )
                                db_session.add(trainer)
                            market_runner.trainer_id = trainer.id
    db_session.commit()

# Banner
print('Betfair Metadata Retriever V1.0')
print('===============================')
print('')

# Read secrets
with open('secrets.json') as f:
    secrets = json.loads(f.read())

# Create DB engine and session factory
db_engine = sql.create_engine(SQLALCHEMY_URL)
Session = sql.orm.sessionmaker(bind=db_engine)

# Create DB session
db_session = Session()
print('DB session created')

# Logon to Betfair
betfair_api = bfl.APIClient(
    secrets['username'],
    secrets['password'],
    app_key=secrets['betangel_app_key'],
    cert_files=['./certs/client-2048.crt', './certs/client-2048.key'],
    lightweight=False
)
betfair_api.login()
print('Logged on to Betfair')

# Get orders
for event in db_session.query(Event).order_by('open_date', 'name'):
    print(f"Event: {event.name} {event.open_date}")
    get_metadata(db_session, betfair_api, event)

# Logout from Betfair
betfair_api.logout()
print('Logged off from Betfair')
betfair_api = None

## Close DB session
db_session.close()
print('DB session closed')
db_session = None
