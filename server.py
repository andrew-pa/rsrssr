from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import feedparser
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rss_feeds.db"
db = SQLAlchemy(app)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(512), nullable=False)
    title = db.Column(db.String(256), nullable=True)
    etag = db.Column(db.String(128), nullable=True)
    modified = db.Column(db.String(128), nullable=True)
    items = db.relationship(
        "Item", backref="feed", lazy=True, cascade="all, delete-orphan"
    )


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    link = db.Column(db.String(512), nullable=False)
    published = db.Column(db.DateTime, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(128), nullable=True)
    feed_id = db.Column(
        db.Integer, db.ForeignKey("feed.id"), nullable=False, index=True
    )


with app.app_context():
    db.create_all()


@app.template_filter("format_date")
def format_date(value, format="%d %B %Y, %I:%M %p"):
    if value is None:
        return ""
    return value.strftime(format)


def datetime_from_time(t):
    return datetime.fromtimestamp(time.mktime(t))


def update_feed(feed, data):
    feed.title = data.feed.title
    feed.etag = data.get("etag", None)
    feed.modified = data.get("modified", None)
    feed_pub_date = data.feed.get(
        "published_parsed", data.feed.get("updated_parsed", time.localtime())
    )
    most_recent_item = db.session.query(Item.published).filter_by(
        feed_id=feed.id
    ).order_by(Item.published.desc()).first() or (
        datetime.now() - relativedelta(months=2)
    )
    db.session.add_all(
        filter(
            lambda item: item.published >= most_recent_item,
            (
                Item(
                    title=entry.title or "?",
                    link=entry.link,
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


def update_feeds():
    num_failed = 0
    num_updated = 0
    num_feeds = 0
    for feed in Feed.query:
        num_feeds += 1
        try:
            data = feedparser.parse(feed.url, etag=feed.etag, modified=feed.modified)
            if len(data.entries) > 0:
                update_feed(feed, data)
                num_updated += 1
        except Exception as e:
            print(f"failed to load feed {feed}: {e}")
            num_failed += 1
    db.session.commit()
    return num_feeds, num_failed, num_updated


@app.route("/")
def index():
    start_time = time.time()
    (num_feeds, num_failed, num_updated) = update_feeds()
    update_time = time.time()
    items = db.session.query(Item).order_by(Item.published.desc()).limit(128).all()
    load_time = time.time()
    return render_template(
        "index.html",
        items=items,
        load_time=round(load_time - update_time, 3),
        update_time=round(update_time - start_time, 3),
        feed_count=num_feeds,
        failed_feed_count=num_failed,
        updated_feed_count=num_updated,
    )


@app.route("/feeds", methods=["GET", "POST"])
def manage_feeds():
    if request.method == "POST":
        if "delete" in request.form:
            feed = Feed.query.get(request.form["delete"])
            db.session.delete(feed)
        else:
            new_feed = Feed()
            new_feed.url = request.form["url"]
            db.session.add(new_feed)
        db.session.commit()
        return redirect(url_for("manage_feeds"))

    feeds = Feed.query.all()
    return render_template("feeds.html", feeds=feeds)


@app.route("/static/<path:path>")
def send_static(path):
    return app.send_static_file(path)


if __name__ == "__main__":
    app.run(debug=True)
