import datetime
import json
from time import sleep

import sqlalchemy as sql

import betfairlightweight as bfl

from models import Event, Market, Runner, MarketBook, RunnerBook


def get_events(db_session, betfair_api, date):

    events = []
    bfl_event_results = betfair_api.betting.list_events(
        filter = bfl.filters.market_filter(
            event_type_ids = [7],
            market_countries = ['GB', 'IE'],
            market_type_codes=['WIN'],
            market_start_time={
                'from': date.strftime("%Y-%m-%dT%TZ"),
                'to': (date + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%TZ"),
            },
        )
    )
    for bfl_event_result in bfl_event_results:
        bfl_event = bfl_event_result.event
        event = db_session.query(Event).filter(Event.betfair_id==bfl_event.id).one_or_none()
        if not event:
            event = Event(
                betfair_id=bfl_event.id,
                name=bfl_event.name,
                country_code=bfl_event.country_code,
                time_zone=bfl_event.time_zone,
                venue=bfl_event.venue,
                open_date=bfl_event.open_date
            )
            db_session.add(event)
        events.append(event)
        db_session.commit()
    return events


def get_markets(db_session, betfair_api, event):

    markets = []
    bfl_markets = betfair_api.betting.list_market_catalogue(
        filter = bfl.filters.market_filter(
            event_ids = [event.betfair_id],
            market_type_codes=['WIN'],
        ),
        max_results=25,
        market_projection=['MARKET_START_TIME', 'RUNNER_DESCRIPTION']
    )
    for bfl_market in bfl_markets:
        market = db_session.query(Market).filter(Market.betfair_id==bfl_market.market_id).one_or_none()
        if not market:
            market = Market(
                event_id=event.id,
                betfair_id=bfl_market.market_id,
                name=bfl_market.market_name,
                start_time=bfl_market.market_start_time,
                total_matched=bfl_market.total_matched
            )
            db_session.add(market)
            for bfl_runner in bfl_market.runners:
                runner = db_session.query(Runner).filter(Runner.betfair_id==bfl_runner.selection_id).one_or_none()
                if not runner:
                    runner = Runner(
                        market_id=market.id,
                        betfair_id=bfl_runner.selection_id,
                        name=bfl_runner.runner_name,
                        sort_priority=bfl_runner.sort_priority
                    )
                    db_session.add(runner)
        markets.append(market)
        db_session.commit()
    return markets


def get_market_book(db_session, betfair_api, market):

    market_book = None
    #print(f"  {datetime.datetime.now()}: Sending API request")
    bfl_market_books = betfair_api.betting.list_market_book([market.betfair_id])
    #print(f"  {datetime.datetime.now()}: API response received")
    if bfl_market_books:
        bfl_market_book = bfl_market_books[0]
        market_book = MarketBook(
            market_id = market.id,
            date_time = datetime.datetime.now(),
            delayed = bfl_market_book.is_market_data_delayed,
            status = bfl_market_book.status,
            bet_delay = bfl_market_book.bet_delay,
            bsp_reconciled = bfl_market_book.bsp_reconciled,
            complete = bfl_market_book.complete,
            inplay = bfl_market_book.inplay,
            number_of_winners = bfl_market_book.number_of_winners,
            number_of_runners = bfl_market_book.number_of_runners,
            number_of_active_runners = bfl_market_book.number_of_active_runners,
            last_match_time = bfl_market_book.last_match_time,
            total_matched = bfl_market_book.total_matched,
            total_available = bfl_market_book.total_available,
            cross_matching = bfl_market_book.cross_matching,
            runners_voidable = bfl_market_book.runners_voidable,
            version = 0 #bfl_market_book.version
        )
        db_session.add(market_book)
        #print(f"  {datetime.datetime.now()}: Market book created")
        for bfl_runner_book in bfl_market_book.runners:
            runner = db_session.query(Runner).filter(Runner.betfair_id==bfl_runner_book.selection_id).one_or_none()
            if runner:
                runner_book = RunnerBook(
                    market_book_id = market_book.id,
                    runner_id = runner.id,
                    handicap = bfl_runner_book.handicap,
                    status = bfl_runner_book.status,
                    adjustment_factor = bfl_runner_book.adjustment_factor,
                    last_price_traded = bfl_runner_book.last_price_traded,
                    total_matched = bfl_runner_book.total_matched,
                    removal_date = bfl_runner_book.removal_date
                )
                db_session.add(runner_book)
        #print(f"  {datetime.datetime.now()}: Runner books created")
        db_session.commit()
        #print(f"  {datetime.datetime.now()}: DB changes committed")
    return market_book


# DB connection URL
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'
SQLALCHEMY_URL = 'postgresql://postgres:barnum@localhost/betfairlogger'

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
    app_key=secrets['betangel_app_key'],
    cert_files=['./certs/client-2048.crt', './certs/client-2048.key'],
    lightweight=False
)
betfair_api.login()

# Create DB session
db_session = Session()

# Catch exceptions to make sure that Betfair API and DB are closed down properly
try:

    # Get events and markets for today
    today = datetime.date.today()
    events = get_events(db_session, betfair_api, today)
    markets = []
    for event in events:
        markets += get_markets(db_session, betfair_api, event)

    # Poll each second to update market books - stop when all markets are closed
    markets_open = len(markets)
    while markets_open > 0:

        # Scan markets to see which ones need to be updated
        markets_open = 0
        update_markets = []
        for market in markets:

            # Check if market is open
            if not market.last_book or (market.last_book.status != 'CLOSED'):
                markets_open += 1

                # Get time to start and time since last poll
                secs_to_start = (market.start_time - datetime.datetime.now()).total_seconds()
                secs_since_last_poll = (datetime.datetime.now() - market.last_book.date_time).total_seconds() if market.last_book else 3600
                
                # Update market if less than 15 mins until start
                if secs_to_start <= 900:
                    update_markets.append(market)
                
                # Update market if less than 60 mins until start and more than 10 seconds since last update
                elif (secs_to_start <= 3600) and (secs_since_last_poll > 10):
                    update_markets.append(market)

        # Update markets (this could be done in a single API call for multiple markets but
        # that could lead to complications with amount of data and open vs closed markets)
        for market in update_markets:
            print(f"{datetime.datetime.now()}: Updating {market.event.name} {market.name} {market.start_time}")
            market_book = get_market_book(db_session, betfair_api, market)
            market.last_book_id = market_book.id
            db_session.commit()
            #print(f"  {datetime.datetime.now()}: Last market book updated")

        # Pause for a second
        if markets_open > 0:
            sleep(1)

finally:
    # Logout from Betfair
    betfair_api.logout()

    # Close DB session
    db_session.close()


