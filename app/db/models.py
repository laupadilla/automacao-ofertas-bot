from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer,
    Boolean, DateTime, Text
)
from app.db.database import Base

class Product(Base):
    __tablename__ = "products"

    asin            = Column(String, primary_key=True)
    title           = Column(Text)
    price           = Column(Float)
    original_price  = Column(Float)
    discount        = Column(Integer)
    rating          = Column(Float)
    review_count    = Column(Integer)
    category        = Column(String(100))
    image_url       = Column(Text)
    affiliate_url   = Column(Text)
    features        = Column(Text)
    scraped_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SentProduct(Base):
    __tablename__ = "sent_products"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    asin         = Column(String, index=True)
    channel_id   = Column(String)
    sent_at      = Column(DateTime, default=datetime.utcnow)
    message_text = Column(Text)

class DailyQueue(Base):
    __tablename__ = "daily_queue"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    asin             = Column(String, index=True)
    category         = Column(String(100))
    title_short      = Column(Text)
    message_telegram = Column(Text)
    affiliate_url    = Column(Text)
    image_url        = Column(Text)
    price            = Column(Float)
    discount         = Column(Integer)
    scheduled_time   = Column(String(5))
    sent             = Column(Boolean, default=False)
    queue_date       = Column(String(10))
    created_at       = Column(DateTime, default=datetime.utcnow)