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
    runners = relationship('Runner', order_by='Runner.sort_priority', backref='market')
    books = relationship('MarketBook', primaryjoin='MarketBook.market_id==Market.id', order_by='MarketBook.date_time', backref='market')
    last_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True, index = True)
    last_book = relationship('MarketBook', foreign_keys=[last_book_id])
    last_prerace_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True, index = True)
    last_prerace_book = relationship('MarketBook', foreign_keys=[last_prerace_book_id])
    last_inplay_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True, index = True)
    last_inplay_book = relationship('MarketBook', foreign_keys=[last_inplay_book_id])


class Runner(Base):

    __tablename__ = 'runner'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False, index = True)
    betfair_id = Column(BigInteger, nullable=False, index = True)
    name = Column(String, nullable=False)
    sort_priority = Column(Integer, nullable=False)
    books = relationship('RunnerBook', backref='runner')
    #metadata

    @property
    def starting_price(self):
        session = Session.object_session(self)
        last_prerace_book = session.query(RunnerBook).filter(RunnerBook.runner_id == self.id, RunnerBook.market_book_id == self.market.last_prerace_book_id).one_or_none()
        return last_prerace_book.last_price_traded if last_prerace_book else None


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
    runners = relationship('RunnerBook', backref='market_book')
    #key_line_description

class RunnerBook(Base):

    __tablename__ = 'runner_book'

    id = Column(Integer, primary_key=True)
    market_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=False, index = True)
    runner_id = Column(Integer, ForeignKey('runner.id'), nullable=False, index = True)
    handicap = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    adjustment_factor =  Column(Float, nullable=False)
    last_price_traded = Column(Float, nullable=True)
    total_matched = Column(Float, nullable=True)
    removal_date = Column(DateTime, nullable=True)
    #starting_price
    #exchange_prices
    #orders
    #matches
    #matches_by_strategy
