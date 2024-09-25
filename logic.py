from typing import Any
import time
import sqlalchemy

import datetime
import pandas as pd

from sqlalchemy.orm import Session, scoped_session

from update import update_feed

from models import Base, Item, Feed, UpdateStat

PAGE_SIZE = 48


def last_update_stats(session: scoped_session) -> UpdateStat | None:
    last_stats = (
        session.query(UpdateStat).order_by(UpdateStat.timestamp.desc()).limit(1).first()
    )
    if last_stats:
        last_stats.dur_total = round(last_stats.dur_total, 3)
    return last_stats


def item_list(
    session: scoped_session, offset: int, specific_feed_id: int | None
) -> dict[str, Any]:
    start_time = time.time()

    items_query = session.query(Item).order_by(Item.published.desc())
    if specific_feed_id:
        items_query = items_query.where(Item.feed_id == specific_feed_id)
    items = items_query.offset(offset).limit(PAGE_SIZE).all()

    last_stats = last_update_stats(session)

    specific_feed = None
    if specific_feed_id:
        specific_feed = session.query(Feed).get(specific_feed_id)

    load_time = time.time()

    return {
        "items": items,
        "load_time": round(load_time - start_time, 3),
        "last_stats": last_stats,
        "prev_page": offset - PAGE_SIZE if offset > PAGE_SIZE else 0,
        "next_page": offset + PAGE_SIZE,
        "from_feed": specific_feed,
    }


def overview(session: scoped_session) -> dict[str, Any]:
    start_time = time.time()

    five_days_ago = datetime.datetime.now() - datetime.timedelta(days=5)

    # Subquery to get the maximum published date for each feed within the last three days
    subquery = (
        session.query(
            Item.feed_id, sqlalchemy.func.max(Item.published).label("max_published")
        )
        .filter(Item.published >= five_days_ago)
        .group_by(Item.feed_id)
        .subquery()
    )

    # Query to fetch feeds that have items in the last three days, along with their max published date
    feeds_with_max = (
        session.query(Feed, subquery.c.max_published)
        .join(subquery, Feed.id == subquery.c.feed_id)
        .order_by(subquery.c.max_published.desc())
        .all()
    )

    items_by_feed = []

    for feed, _ in feeds_with_max:
        recent_items = (
            session.query(Item)
            .filter(Item.feed_id == feed.id, Item.published >= five_days_ago)
            .order_by(Item.published.desc())
            .limit(5)
            .all()
        )

        # Append the feed and its items to the result list
        items_by_feed.append(
            {"id": feed.id, "title": feed.title, "items": recent_items}
        )

    last_stats = last_update_stats(session)

    load_time = time.time()

    return {
        "feeds": items_by_feed,
        "load_time": round(load_time - start_time, 3),
        "last_stats": last_stats,
    }


def add_feed(session: scoped_session, url: str):
    new_feed = Feed(url=url)
    update_feed(session, new_feed)
    session.add(new_feed)
    session.commit()


def delete_feed(session: scoped_session, id: int):
    feed = session.query(Feed).get(id)
    session.delete(feed)
    session.commit()


def feed_list(session: scoped_session):
    feeds = session.query(Feed).order_by(Feed.last_updated.desc()).all()
    return {"feeds": feeds}


def fetch_update_stats(session: scoped_session, timeframe: str) -> pd.DataFrame:
    timeframe_expr = {
        "day": "-1 day",
        "week": "-7 days",
        "month": "-1 month",
    }.get(timeframe)
    return pd.read_sql_query(
        f"""
        SELECT
        update_stats.*,
        min_feed.url AS min_feed_url,
        max_feed.url AS max_feed_url
        FROM update_stats
        LEFT JOIN feed min_feed ON update_stats.dur_min_feed_id = min_feed.id
        LEFT JOIN feed max_feed ON update_stats.dur_max_feed_id = max_feed.id
        WHERE update_stats.timestamp >= DATE("now", "{timeframe_expr}")
    """,
        con=session.connection(),
    )
