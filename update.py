import time
import feedparser
from statistics import mean, stdev
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Item, Feed, UpdateStat

engine = create_engine("sqlite:///instance/rss_feeds.db")

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def datetime_from_time(t):
    return datetime.fromtimestamp(time.mktime(t))


def get_last_published_date(session, feed):
    most_recent_item = (
        session.query(Item.published)
        .filter_by(feed_id=feed.id)
        .order_by(Item.published.desc())
        .first()
    )

    if most_recent_item:
        return most_recent_item.published
    else:
        return datetime.now() - relativedelta(months=2)


def update_feed(session, feed):
    print(f"updating feed {feed.url} (#{feed.id})")
    start_time = time.time()
    data = feedparser.parse(feed.url, etag=feed.etag, modified=feed.modified)
    if data.status == 304:
        end_time = time.time()
        return {
            "id": feed.id,
            "num_new_items": 0,
            "dur": (end_time - start_time) * 1000,
            "cache_miss": False,
        }
    session.add(feed)
    feed.title = data.feed.get("title", feed.title or feed.url)
    feed.etag = data.get("etag", None)
    feed.modified = data.get("modified", None)
    feed.last_updated = datetime.now()
    feed_pub_date = data.feed.get(
        "published_parsed", data.feed.get("updated_parsed", time.localtime())
    )
    last_published_date = get_last_published_date(session, feed)
    items = list(
        filter(
            lambda item: item.published > last_published_date,
            (
                Item(
                    title=entry.get("title", entry.get("link", "Untitled Item")),
                    link=entry.get(
                        "link", 'javascript:alert("no link provided for item")'
                    ),
                    published=datetime_from_time(
                        entry.get(
                            "published_parsed",
                            entry.get("updated_parsed", feed_pub_date),
                        )
                    ),
                    description=entry.get("description", None),
                    author=entry.get("author", None),
                    feed=feed,
                )
                for entry in data.entries
            ),
        )
    )
    session.add_all(items)
    end_time = time.time()
    return {
        "id": feed.id,
        "num_new_items": len(items),
        "dur": (end_time - start_time) * 1000,
        "cache_miss": True,
    }


def update_feeds(session):
    timestamp = datetime.now()
    start_time = time.time()
    num_failed = 0
    feeds = session.query(Feed).all()
    feed_update_stats = []
    print(f"updating {len(feeds)} feeds")
    for feed in feeds:
        # only update uncached feeds every 6 hours
        if (
            feed.etag is None
            and feed.modified is None
            and feed.last_updated is not None
            and abs(feed.last_updated - datetime.now()) < timedelta(hours=6)
        ):
            continue
        try:
            feed_update_stats.append(update_feed(session, feed))
        except Exception as e:
            print(f"failed to load feed #{feed.id} ({feed.url}): {e}")
            num_failed += 1
    session.commit()
    end_time = time.time()
    min_feed_stat = min(feed_update_stats, key=lambda s: s["dur"], default=None)
    max_feed_stat = max(feed_update_stats, key=lambda s: s["dur"], default=None)
    return UpdateStat(
        timestamp=timestamp,
        num_feeds=len(feeds),
        num_fetched=len(feed_update_stats),
        num_updated=sum(1 for s in feed_update_stats if s["cache_miss"]),
        num_failed=num_failed,
        num_new_items=sum(stats["num_new_items"] for stats in feed_update_stats),
        dur_total=end_time - start_time,
        dur_min_feed=min_feed_stat["dur"] if min_feed_stat else 0,
        dur_min_feed_id=min_feed_stat["id"] if min_feed_stat else None,
        dur_avg_feed=(
            mean(s["dur"] for s in feed_update_stats)
            if len(feed_update_stats) > 0
            else 0
        ),
        dur_std_feed=(
            stdev(s["dur"] for s in feed_update_stats)
            if len(feed_update_stats) >= 2
            else 0
        ),
        dur_max_feed=max_feed_stat["dur"] if max_feed_stat else 0,
        dur_max_feed_id=max_feed_stat["id"] if max_feed_stat else None,
    )


if __name__ == "__main__":
    session = Session()
    stats = update_feeds(session)
    print(f"update took {stats.dur_total}s")
    session.add(stats)
    session.commit()
    print("finished!")
