import datetime
import json

import sqlalchemy as sql

import betfairlightweight as bfl

from models import Event, Market, Runner

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'

# Read secrets
with open('secrets.json') as f:
    secrets = json.loads(f.read())

# Create DB engine and open a session
db_engine = sql.create_engine(SQLALCHEMY_URL)
Session = sql.orm.sessionmaker(bind=db_engine)

# Logon to Betfair
betfair_api = bfl.APIClient(
    secrets['username'],
    secrets['password'],
    app_key=secrets['app_key'],
    cert_files=['./certs/client-2048.crt', './certs/client-2048.key'],
    lightweight=False
)
betfair_api.login()

# Create/update GB and IRE horse racing events for today
events = betfair_api.betting.list_events(
    filter = bfl.filters.market_filter(
        event_type_ids = [7],
        market_countries = ['GB', 'IE'],
        market_type_codes=['WIN'],
        market_start_time={
            'from': datetime.datetime.today().strftime("%Y-%m-%dT%TZ"),
            'to': (datetime.datetime.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%TZ"),
        },
    )
)
db_session = Session()
for event in events:
    event = event.event
    print(event.name)
    db_event = db_session.query(Event).filter(Event.betfair_id==event.id).one_or_none()
    if not db_event:
        db_event = Event(betfair_id=event.id, name=event.name, venue=event.venue)
        db_session.add(db_event)
        db_session.commit()
    markets = betfair_api.betting.list_market_catalogue(
        filter = bfl.filters.market_filter(
            event_ids = [event.id],
            market_type_codes=['WIN'],
        ),
        max_results=10,
        market_projection=['MARKET_START_TIME', 'RUNNER_DESCRIPTION']
    )
    for market in markets:
        print(f'  {market.market_name}')
        db_market = db_session.query(Market).filter(Market.betfair_id==market.market_id).one_or_none()
        if not db_market:
            db_market = Market(event_id=db_event.id, betfair_id=market.market_id, name=market.market_name, start_time=market.market_start_time, total_matched=market.total_matched)
            db_session.add(db_market)
            db_session.commit()
        for runner in market.runners:
            print(f'    {runner.runner_name}')
            db_runner = db_session.query(Runner).filter(Runner.betfair_id==runner.selection_id).one_or_none()
            if not db_runner:
                db_runner = Runner(market_id=db_market.id, betfair_id=runner.selection_id, name=runner.runner_name, sort_priority=runner.sort_priority)
                db_session.add(db_runner)
                db_session.commit()

# Logout from Betfair
betfair_api.logout()

# Close DB session
db_session.close()
