from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, Time, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

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
    last_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=True)
    last_book = relationship('MarketBook', foreign_keys=[last_book_id])



class Runner(Base):

    __tablename__ = 'runner'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False)
    betfair_id = Column(BigInteger, nullable=False)
    name = Column(String, nullable=False)
    sort_priority = Column(Integer, nullable=False)
    #metadata
    books = relationship('RunnerBook', backref='runner')


class MarketBook(Base):

    __tablename__ = 'market_book'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False)
    date_time = Column(DateTime, nullable=False)
    delayed = Column(Boolean)
    status = Column(String, nullable=False)
    bet_delay = Column(Integer, nullable=False)
    bsp_reconciled = Column(Boolean)
    complete = Column(Boolean)
    inplay = Boolean()
    number_of_winners = Column(Integer, nullable=False)
    number_of_runners = Column(Integer, nullable=False)
    number_of_active_runners = Column(Integer, nullable=False)
    last_match_time = Column(DateTime, nullable=True)
    total_matched = Column(Float, nullable=False)
    total_available = Column(Float, nullable=False)
    cross_matching = Boolean()
    runners_voidable = Boolean()
    version = Column(BigInteger, nullable=False)
    runners = relationship('RunnerBook', backref='market_book')
    #key_line_description

class RunnerBook(Base):

    __tablename__ = 'runner_book'

    id = Column(Integer, primary_key=True)
    market_book_id = Column(Integer, ForeignKey('market_book.id'), nullable=False)
    runner_id = Column(Integer, ForeignKey('runner.id'), nullable=False)
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