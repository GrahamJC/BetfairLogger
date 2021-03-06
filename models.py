from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, Time, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Session, relationship

Base = declarative_base()

class Event(Base):

    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    betfair_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    country_code = Column(String, nullable=False)
    time_zone = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    open_date = Column(DateTime, nullable=False)
    markets = relationship('Market', order_by='Market.start_time', backref='event')


class Market(Base):

    __tablename__ = 'market'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    betfair_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    total_matched = Column(Float, nullable=False)
    notes = Column(String, nullable = True)
    runners = relationship('MarketRunner', order_by='MarketRunner.sort_priority', backref='market')
    books = relationship('MarketBook', primaryjoin='MarketBook.market_id==Market.id', order_by='MarketBook.date_time', backref='market')
    last_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True, index = True)
    last_prerace_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True, index = True)
    last_inplay_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True, index = True)
    orders = relationship('MarketRunnerOrder', order_by='MarketRunnerOrder.placed_date', backref='market')

    @property
    def last_book(self):
        session = Session.object_session(self)
        return (
            session.query(MarketBook)
                .filter(MarketBook.market_id == self.id)
                .order_by(MarketBook.date_time.desc())
                .first()
        )

    @property
    def last_prerace_book(self):
        session = Session.object_session(self)
        return (
            session.query(MarketBook)
                .filter(MarketBook.market_id == self.id, MarketBook.status == 'OPEN', MarketBook.inplay == False)
                .order_by(MarketBook.date_time.desc())
                .first()
        )

    @property
    def last_inplay_book(self):
        session = Session.object_session(self)
        return (
            session.query(MarketBook)
                .filter(MarketBook.market_id == self.id, MarketBook.status == 'OPEN', MarketBook.inplay == True)
                .order_by(MarketBook.date_time.desc())
                .first()
        )

    @property
    def profit(self):
        return sum([o.profit for o in self.orders])


class Runner(Base):

    __tablename__ = 'runner'

    id = Column(Integer, primary_key=True)
    betfair_id = Column(BigInteger, nullable=False, index = True)
    name = Column(String, nullable=False)
    markets = relationship('MarketRunner', backref='runner')

class Jockey(Base):

    __tablename__ = 'jockey'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class Trainer(Base):

    __tablename__ = 'trainer'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class MarketRunner(Base):

    __tablename__ = 'market_runner'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False, index = True)
    runner_id = Column(Integer, ForeignKey('runner.id'), nullable=False, index = True)
    jockey_id = Column(Integer, ForeignKey('jockey.id'), nullable=True, index = True)
    trainer_id = Column(Integer, ForeignKey('trainer.id'), nullable=True, index = True)
    sort_priority = Column(Integer, nullable=False)
    books = relationship('MarketRunnerBook', backref='market_runner')
    orders = relationship('MarketRunnerOrder', order_by='MarketRunnerOrder.placed_date', backref='market_runner')
    #metadata

    @property
    def last_book(self):
        session = Session.object_session(self)
        return (
            session.query(MarketRunnerBook)
                .join(MarketBook)
                .filter(MarketRunnerBook.market_runner_id == self.id)
                .order_by(MarketBook.date_time.desc())
                .first()
        )

    @property
    def last_prerace_book(self):
        session = Session.object_session(self)
        return (
            session.query(MarketRunnerBook)
                .join(MarketBook)
                .filter(MarketRunnerBook.market_runner_id == self.id, MarketBook.status == 'OPEN', MarketBook.inplay == False)
                .order_by(MarketBook.date_time.desc())
                .first()
        )

    @property
    def last_inplay_book(self):
        session = Session.object_session(self)
        return (
            session.query(MarketRunnerBook)
                .join(MarketBook)
                .filter(MarketRunnerBook.market_runner_id == self.id, MarketBook.status == 'OPEN', MarketBook.inplay == True)
                .order_by(MarketBook.date_time.desc())
                .first()
        )
    @property
    def starting_price(self):
        last_prerace_book = self.last_prerace_book
        result = last_prerace_book.last_price_traded if last_prerace_book else None
        return result or 1000


class MarketBook(Base):

    __tablename__ = 'market_book'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False, index = True)
    date_time = Column(DateTime, nullable=False)
    delayed = Column(Boolean)
    status = Column(String, nullable=False)
    bet_delay = Column(Integer, nullable=False)
    bsp_reconciled = Column(Boolean, nullable=False)
    complete = Column(Boolean, nullable=False)
    inplay = Column(Boolean, nullable=False)
    number_of_winners = Column(Integer, nullable=False)
    number_of_runners = Column(Integer, nullable=False)
    number_of_active_runners = Column(Integer, nullable=False)
    last_match_time = Column(DateTime, nullable=True)
    total_matched = Column(Float, nullable=False)
    total_available = Column(Float, nullable=False)
    cross_matching = Column(Boolean, nullable=False)
    runners_voidable = Column(Boolean, nullable=False)
    version = Column(BigInteger, nullable=False)
    runners = relationship('MarketRunnerBook', backref='market_book')

class MarketRunnerBook(Base):

    __tablename__ = 'market_runner_book'

    id = Column(Integer, primary_key=True)
    market_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=False, index = True)
    market_runner_id = Column(Integer, ForeignKey('market_runner.id'), nullable=False, index = True)
    handicap = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    adjustment_factor =  Column(Float, nullable=True)
    last_price_traded = Column(Float, nullable=True)
    total_matched = Column(Float, nullable=True)
    removal_date = Column(DateTime, nullable=True)
    back_price = Column(Float, nullable=True)
    wom_back = Column(Float, nullable=True)
    lay_price = Column(Float, nullable=True)
    wom_lay = Column(Float, nullable=True)

class MarketRunnerOrder(Base):

    __tablename__ = 'market_runner_order'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False, index = True)
    market_runner_id = Column(Integer, ForeignKey('market_runner.id'), nullable=False, index = True)
    betfair_id = Column(String, nullable=False)
    placed_date = Column(DateTime, nullable=False)
    side = Column(String, nullable=False)
    size = Column(Float, nullable=False)
    price_requested = Column(Float, nullable=False)
    matched_date = Column(DateTime, nullable=False)
    price_matched = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)


