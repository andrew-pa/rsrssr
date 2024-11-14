from typing import Any
import time
import sqlalchemy

import datetime
import pandas as pd

from sqlalchemy.orm import scoped_session

from update import update_feed

from models import Item, Feed, UpdateStat

# number of items per page
PAGE_SIZE = 48

# number of decimal places for printing durations
TIMING_PRECISION = 3


def last_update_stats(session: scoped_session) -> UpdateStat | None:
    last_stats = (
        session.query(UpdateStat).order_by(UpdateStat.timestamp.desc()).limit(1).first()
    )
    if last_stats:
        last_stats.dur_total = round(last_stats.dur_total, TIMING_PRECISION)
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
        "load_time": round(load_time - start_time, TIMING_PRECISION),
        "last_stats": last_stats,
        "prev_page": offset - PAGE_SIZE if offset > PAGE_SIZE else 0,
        "next_page": offset + PAGE_SIZE,
        "from_feed": specific_feed,
    }


# maximum age of each item displayed
OVERVIEW_NUM_DAYS_SINCE = 14
# maximum number of items to display per feed
OVERVIEW_ITEMS_PER_FEED = 7


def overview(session: scoped_session) -> dict[str, Any]:
    start_time = time.time()

    since_date = datetime.datetime.now() - datetime.timedelta(
        days=OVERVIEW_NUM_DAYS_SINCE
    )

    # Subquery to get the maximum published date and count of items for each feed
    subquery = (
        session.query(
            Item.feed_id,
            sqlalchemy.func.max(Item.published).label("max_published"),
            sqlalchemy.func.count(Item.id).label("item_count")
        )
        .filter(Item.published >= since_date, Item.visited == False)
        .group_by(Item.feed_id)
        .subquery()
    )

    # Query to fetch feeds that have items since `since_date`, along with their max published date and item count
    feeds_with_max = (
        session.query(Feed, subquery.c.max_published, subquery.c.item_count)
        .join(subquery, Feed.id == subquery.c.feed_id)
        .order_by(subquery.c.max_published.desc(), subquery.c.item_count.asc())
        .all()
    )

    items_by_feed = []

    for feed, _, _ in feeds_with_max:
        recent_items = (
            session.query(Item)
            .filter(
                Item.feed_id == feed.id,
                Item.published >= since_date,
                Item.visited == False,
            )
            .order_by(Item.published.desc())
            .limit(OVERVIEW_ITEMS_PER_FEED)
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
        "load_time": round(load_time - start_time, TIMING_PRECISION),
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


def record_visit(session: scoped_session, item_id: int):
    item = session.query(Item).get(item_id)
    if item:
        item.visited = True
    session.commit()
