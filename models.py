from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Feed(Base):
    __tablename__ = "feed"
    id = Column(Integer, primary_key=True)
    url = Column(String(512), nullable=False)
    title = Column(String(256), nullable=True)
    etag = Column(String(128), nullable=True)
    modified = Column(String(128), nullable=True)
    last_updated = Column(DateTime, nullable=True)
    downrank = Column(Boolean, nullable=False, default=False)
    items = relationship(
        "Item", backref="feed", lazy=True, cascade="all, delete-orphan"
    )


class Item(Base):
    __tablename__ = "item"
    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    link = Column(String(512), nullable=False)
    published = Column(DateTime, nullable=False, index=True)
    description = Column(Text, nullable=True)
    author = Column(String(128), nullable=True)
    visited = Column(DateTime, nullable=True, index=True)
    liked = Column(DateTime, nullable=True, index=True)
    feed_id = Column(Integer, ForeignKey("feed.id"), nullable=False, index=True)


class UpdateStat(Base):
    __tablename__ = "update_stats"
    timestamp = Column(DateTime, nullable=False, primary_key=True)
    num_feeds = Column(Integer, nullable=False)
    num_fetched = Column(Integer, nullable=False)
    num_updated = Column(Integer, nullable=False)
    num_failed = Column(Integer, nullable=False)
    num_new_items = Column(Integer, nullable=False)
    dur_total = Column(Float, nullable=False)
    dur_min_feed = Column(Float, nullable=False)
    dur_min_feed_id = Column(Float, ForeignKey("feed.id"), nullable=True)
    dur_avg_feed = Column(Float, nullable=False)
    dur_std_feed = Column(Float, nullable=False)
    dur_max_feed = Column(Float, nullable=False)
    dur_max_feed_id = Column(Float, ForeignKey("feed.id"), nullable=True)
