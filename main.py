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


def get_events(db_session, betfair_api, date):

    events = []
    bfl_event_results = betfair_api.betting.list_events(
        filter = bfl.filters.market_filter(
            event_type_ids = [7],
            market_countries = ['GB', 'IE'],
            market_type_codes = ['WIN'],
            market_start_time = {
                'from': date.strftime("%Y-%m-%dT%TZ"),
                'to': (date + datetime.timedelta(days = 1)).strftime("%Y-%m-%dT%TZ"),
            },
        )
    )
    for bfl_event_result in bfl_event_results:
        bfl_event = bfl_event_result.event
        event = db_session.query(Event).filter(Event.betfair_id==bfl_event.id).one_or_none()
        if not event:
            print(f"New event: {bfl_event.name} ({bfl_event.country_code})")
            event = Event(
                betfair_id = bfl_event.id,
                name = bfl_event.name,
                country_code = bfl_event.country_code,
                time_zone = bfl_event.time_zone,
                venue = bfl_event.venue,
                open_date = bfl_event.open_date
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
        market = db_session.query(Market).filter(Market.event_id == event.id, Market.betfair_id == bfl_market.market_id).one_or_none()
        if not market:
            print(f"New market: {bfl_market.market_start_time}: {bfl_market.market_name} ({len(bfl_market.runners)} runners)")
            market = Market(
                event_id = event.id,
                betfair_id = bfl_market.market_id,
                name = bfl_market.market_name,
                start_time = bfl_market.market_start_time,
                total_matched = bfl_market.total_matched
            )
            db_session.add(market)
        markets.append(market)
        for bfl_runner in bfl_market.runners:
            runner = db_session.query(Runner).filter(Runner.betfair_id == bfl_runner.selection_id).one_or_none()
            if not runner:
                runner = Runner(
                    betfair_id = bfl_runner.selection_id,
                    name = bfl_runner.runner_name,
                )
                db_session.add(runner)
            market_runner = db_session.query(MarketRunner).filter(MarketRunner.market_id == market.id, MarketRunner.runner_id == runner.id).one_or_none()
            if not market_runner:
                market_runner = MarketRunner(
                    market_id = market.id,
                    runner_id = runner.id,
                    sort_priority = bfl_runner.sort_priority
                )
                db_session.add(market_runner)
    db_session.commit()
    return markets


def get_market_book(db_session, betfair_api, market):

    market_book = None
    #print(f"  {datetime.datetime.now()}: Sending API request")
    bfl_market_books = betfair_api.betting.list_market_book(
        [market.betfair_id],
        bfl.filters.price_projection(
            price_data = bfl.filters.price_data(ex_best_offers = True)
        )
    )
    #print(f"  {datetime.datetime.now()}: API response received")
    if bfl_market_books:
        bfl_market_book = bfl_market_books[0]

        # Ignore suspended markets if the previous update was also suspended
        if (bfl_market_book.status != 'SUSPENDED') or not market.last_book or (market.last_book.status != 'SUSPENDED'):
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
                version = bfl_market_book.version
            )
            db_session.add(market_book)
            #print(f"  {datetime.datetime.now()}: Market book created")
            for bfl_runner_book in bfl_market_book.runners:
                runner = db_session.query(Runner).filter(Runner.betfair_id == bfl_runner_book.selection_id).one_or_none()
                if runner:
                    market_runner = db_session.query(MarketRunner).filter(MarketRunner.market_id == market_book.market_id, MarketRunner.runner_id == runner.id).one_or_none()
                    if market_runner:
                        wom_back = None
                        wom_lay = None
                        if len(bfl_runner_book.ex.available_to_lay) == 3:
                            wom_back = sum([price.size for price in bfl_runner_book.ex.available_to_lay])
                        if len(bfl_runner_book.ex.available_to_back) == 3:
                            wom_lay = sum([price.size for price in bfl_runner_book.ex.available_to_back])
                        market_runner_book = MarketRunnerBook(
                            market_book_id = market_book.id,
                            market_runner_id = market_runner.id,
                            handicap = bfl_runner_book.handicap,
                            status = bfl_runner_book.status,
                            adjustment_factor = bfl_runner_book.adjustment_factor,
                            last_price_traded = bfl_runner_book.last_price_traded,
                            total_matched = bfl_runner_book.total_matched,
                            removal_date = bfl_runner_book.removal_date,
                            wom_back = wom_back,
                            wom_lay = wom_lay
                        )
                        db_session.add(market_runner_book)
            #print(f"  {datetime.datetime.now()}: Runner books created")
            db_session.commit()
            #print(f"  {datetime.datetime.now()}: DB changes committed")
    return market_book

def get_market_orders(db_session, betfair_api, market):

    # Get settled orders
    orders = []
    bfl_result = betfair_api.betting.list_cleared_orders(
        bet_status = 'SETTLED',
        market_ids = [market.betfair_id]
    )
    for bfl_order in bfl_result.orders:

        # Don't duplicate orders (just in case)
        order = db_session.query(MarketRunnerOrder).filter(MarketRunnerOrder.betfair_id == bfl_order.bet_id).one_or_none()
        if not order:
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

def log_markets(db_session, betfair_api, date):

    # Get events and markets
    events = get_events(db_session, betfair_api, date)
    markets = []
    for event in events:
        markets += get_markets(db_session, betfair_api, event)

    # Poll to update market books - stop when all markets are closed
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
                
                # Always update market after post time
                if secs_to_start <= 0:
                    update_markets.append(market)
                
                # Update market if less than 10 mins until start and more than 1 second since last update
                elif (secs_to_start <= 600) and (secs_since_last_poll >= 1):
                    update_markets.append(market)
                
                # Update market if less than 20 mins until start and more than 5 seconds since last update
                elif (secs_to_start <= 1200) and (secs_since_last_poll >= 5):
                    update_markets.append(market)
                
                # Update market if less than 30 mins until start and more than 15 seconds since last update
                elif (secs_to_start <= 1800) and (secs_since_last_poll >= 15):
                    update_markets.append(market)
                
                # Update market if less than 60 mins until start and more than 60 seconds since last update
                elif (secs_to_start <= 3600) and (secs_since_last_poll >= 60):
                    update_markets.append(market)

        # Update markets (this could be done in a single API call for multiple markets but
        # that could lead to complications with amount of data and open vs closed markets)
        for market in update_markets:
            print(f"{datetime.datetime.now()}: Updating {market.event.name} {market.name} {market.start_time}")
            market_book = get_market_book(db_session, betfair_api, market)
            if market_book:
                market.last_book_id = market_book.id
                if market_book.status == 'OPEN':
                    if market_book.inplay:
                        market.last_inplay_book_id = market_book.id
                    else:
                        market.last_prerace_book_id = market_book.id
                    db_session.commit()
                elif market_book.status == 'CLOSED':
                    orders = get_market_orders(db_session, betfair_api, market)
                    print(f"{len(orders)} orders retrieved for {market.event.name} {market.name} {market.start_time}")

        # Pause for half a second
        sleep(0.5)


def wait_until(wake_up):

    wait_seconds = (wake_up - datetime.datetime.now()).total_seconds() 
    if wait_seconds > 0:
        print(f"Sleep until {wake_up} ({wait_seconds} seconds)")
        sleep(wait_seconds)


# Banner
print('Betfair Logger V1.0')
print('===================')
print('')

# Read secrets
with open('secrets.json') as f:
    secrets = json.loads(f.read())

# Create DB engine and session factory
db_engine = sql.create_engine(SQLALCHEMY_URL)
Session = sql.orm.sessionmaker(bind=db_engine)

# Run indefinitely
while True:

    try:
        # Wait until 10am
        today = datetime.date.today()
        wait_until(datetime.datetime(today.year, today.month, today.day, 10, 0, 0))

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

        # Log today's markets
        log_markets(db_session, betfair_api, today)

        # Logout from Betfair
        betfair_api.logout()
        print('Logged off from Betfair')
        betfair_api = None

        ## Close DB session
        db_session.close()
        print('DB session closed')
        db_session = None

        # Wait until 10am tomorrow
        tomorrow = today + datetime.timedelta(days = 1)
        wait_until(datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day,10, 0, 0))

    except:
        traceback.print_exc()

    finally:

        try:
            # Logout from Betfair
            if betfair_api:
                betfair_api.logout()
                print('Logged off from Betfair')
                betfair_api = None

            # Close DB session
            if db_session:
                db_session.close()
                print('DB session closed')
                db_session = None

        except:
            # Ignore exceptions
            pass

        # Wait 5 seconds before retrying
        sleep(5)


