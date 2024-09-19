import time
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io
import pandas as pd
import datetime

from update import update_feed

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rss_feeds.db"
db = SQLAlchemy(app)

from models import Base, Item, Feed, UpdateStat

with app.app_context():
    Base.metadata.create_all(bind=db.engine)


@app.template_filter("format_date")
def format_date(value, format="%d %B %Y, %I:%M %p"):
    if value is None:
        return None
    return value.strftime(format)


PAGE_SIZE = 48


@app.route("/")
def index():
    start_time = time.time()
    offset = request.args.get("offset", default=0, type=int)
    specific_feed_id = request.args.get("feed", default=None, type=int)

    items_query = db.session.query(Item).order_by(Item.published.desc())
    if specific_feed_id:
        items_query = items_query.where(Item.feed_id == specific_feed_id)
    items = items_query.offset(offset).limit(PAGE_SIZE).all()

    last_stats = (
        db.session.query(UpdateStat)
        .order_by(UpdateStat.timestamp.desc())
        .limit(1)
        .first()
    )
    if last_stats is None:
        return "<pre>ERROR: You need to run the feed updater first!</pre>"
    specific_feed = None
    if specific_feed_id:
        specific_feed = db.session.query(Feed).get(specific_feed_id)
    load_time = time.time()
    return render_template(
        "index.html",
        items=items,
        load_time=round(load_time - start_time, 3),
        update_time=round(last_stats.dur_total, 3),
        feed_count=last_stats.num_feeds,
        new_item_count=last_stats.num_new_items,
        last_update=last_stats.timestamp,
        prev_page=offset - PAGE_SIZE if offset > PAGE_SIZE else 0,
        next_page=offset + PAGE_SIZE,
        from_feed=specific_feed,
    )


def get_items_grouped(session):
    """
    Retrieves feeds with items from the last five days.

    Args:
        session (Session): SQLAlchemy session connected to the database.

    Returns:
        List[Dict]: A list of dictionaries, each containing the feed title and its recent items.
    """
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

    result = []

    for feed, _ in feeds_with_max:
        recent_items = (
            session.query(Item)
            .filter(Item.feed_id == feed.id, Item.published >= five_days_ago)
            .order_by(Item.published.desc())
            .limit(5)
            .all()
        )

        # Convert items to dictionaries
        items_list = [
            {
                "title": item.title,
                "link": item.link,
                "published": item.published,
                "description": item.description,
                "author": item.author,
            }
            for item in recent_items
        ]

        # Append the feed and its items to the result list
        result.append({"id": feed.id, "title": feed.title, "items": items_list})

    return result


@app.route("/ov")
def overview():
    start_time = time.time()
    feeds = get_items_grouped(db.session)
    load_time = time.time()
    return render_template(
        "overview.html", feeds=feeds, load_time=round(load_time - start_time, 3)
    )


@app.route("/feeds", methods=["GET", "POST"])
def manage_feeds():
    if request.method == "POST":
        if "delete" in request.form:
            feed = db.session.query(Feed).get(request.form["delete"])
            db.session.delete(feed)
        else:
            new_feed = Feed(url=request.form["url"])
            update_feed(db.session, new_feed)
            db.session.add(new_feed)
        db.session.commit()
        return redirect(url_for("manage_feeds"))

    feeds = db.session.query(Feed).order_by(Feed.last_updated.desc()).all()
    return render_template("feeds.html", feeds=feeds)


@app.route("/stats")
def graph_update_stats():
    data = pd.read_sql_query(
        """
        SELECT
        update_stats.*,
        min_feed.url AS min_feed_url,
        max_feed.url AS max_feed_url
        FROM update_stats
        LEFT JOIN feed min_feed ON update_stats.dur_min_feed_id = min_feed.id
        LEFT JOIN feed max_feed ON update_stats.dur_max_feed_id = max_feed.id
        WHERE update_stats.timestamp >= DATE("now", "-1 month")
    """,
        con=db.session.connection(),
    )
    # Create subplots: 2 rows, 2 columns
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Total Update Time and Feed Count",
            "New Items over Time",
            "Fetched, Updated, and Failed",
            "Per-Feed Update Time",
        ),
        specs=[
            [{"secondary_y": True}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
        shared_xaxes=False,
        vertical_spacing=0.1,
        horizontal_spacing=0.1,
    )

    # Plot 1: dur_total and num_feeds with secondary Y axis
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_total"],
            mode="lines",
            name="Total Duration",
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["num_feeds"],
            mode="lines",
            name="Num Feeds",
            yaxis="y2",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Total Duration (s)", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Num Feeds", secondary_y=True, row=1, col=1)

    # Plot 2: num_new_items
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["num_new_items"],
            mode="lines",
            name="Num New Items",
        ),
        row=1,
        col=2,
    )
    fig.update_yaxes(title_text="Num New Items", row=1, col=2)

    # Plot 3: num_fetched, num_updated, num_failed
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"], y=data["num_fetched"], mode="lines", name="Num Fetched"
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"], y=data["num_updated"], mode="lines", name="Num Updated"
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"], y=data["num_failed"], mode="lines", name="Num Failed"
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="Num Feeds", row=2, col=1)

    # Plot 4: dur_min_feed, dur_avg_feed, dur_max_feed with error bars for dur_avg_feed
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_min_feed"],
            mode="lines",
            name="Min Feed Duration",
            text=data["min_feed_url"],
            hovertemplate="%{y}ms; %{text}",
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_avg_feed"],
            mode="lines",
            name="Avg Feed Duration",
            error_y=dict(type="data", array=data["dur_std_feed"], visible=True),
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["dur_max_feed"],
            mode="lines",
            name="Max Feed Duration",
            text=data["max_feed_url"],
            hovertemplate="%{y}ms; %{text}",
        ),
        row=2,
        col=2,
    )
    fig.update_yaxes(title_text="Duration (ms)", row=2, col=2)

    # Update layout for a clean look
    fig.update_layout(title_text="RSS Updates", showlegend=True, hovermode="x unified")

    return plotly.io.to_html(fig)


@app.route("/static/<path:path>")
def send_static(path):
    return app.send_static_file(path)


if __name__ == "__main__":
    app.run(debug=True)
