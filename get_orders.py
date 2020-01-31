import datetime
import json
from time import sleep
import traceback

import sqlalchemy as sql

import betfairlightweight as bfl

from models import Event, Runner, Market, MarketRunner, MarketBook, MarketRunnerBook, MarketRunnerOrder

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@192.168.1.1:32768/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@localhost/betfairlogger'


def get_orders(db_session, betfair_api, event):

    orders = []
    bfl_result = betfair_api.betting.list_cleared_orders(
        bet_status = 'SETTLED',
        event_ids = [event.betfair_id]
    )
    for bfl_order in bfl_result.orders:
        order = db_session.query(MarketRunnerOrder).filter(MarketRunnerOrder.betfair_id == bfl_order.bet_id).one_or_none()
        if not order:
            market = db_session.query(Market).filter(Market.betfair_id == bfl_order.market_id).one_or_none() 
            if market:
                runner = db_session.query(Runner).filter(Runner.betfair_id == bfl_order.selection_id).one_or_none()
                if runner:
                    market_runner = db_session.query(MarketRunner).filter(MarketRunner.market_id == market.id, MarketRunner.runner_id == runner.id).one_or_none()
                    if market_runner:
                        order = MarketRunnerOrder(
                            market_id = market.id,
                            market_runner_id = market_runner.id,
                            betfair_id = bfl_order.bet_id,
                            placed_date = bfl_order.placed_date,
                            side = bfl_order.side,
                            size = bfl_order.size_settled,
                            price_requested = bfl_order.price_requested,
                            matched_date = bfl_order.last_matched_date,
                            price_matched = bfl_order.price_matched,
                            profit = bfl_order.profit,
                        )
                        db_session.add(order)
                        orders.append(order)
    db_session.commit()
    return orders


# Banner
print('Betfair Bet Retriever V1.0')
print('==========================')
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
    orders = get_orders(db_session, betfair_api, event)
    print(f"{len(orders)} orders retrieved for {event.name}")

# Logout from Betfair
betfair_api.logout()
print('Logged off from Betfair')
betfair_api = None

## Close DB session
db_session.close()
print('DB session closed')
db_session = None
