from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class Event(Base):

    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    betfair_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    venue = Column(String, nullable=False)
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


class Runner(Base):

    __tablename__ = 'runner'

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey('market.id'), nullable=False)
    betfair_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    sort_priority = Column(Integer, nullable=False)
