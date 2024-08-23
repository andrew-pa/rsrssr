from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import feedparser
import time
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rss_feeds.db"
db = SQLAlchemy(app)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)


with app.app_context():
    db.create_all()


@app.template_filter("format_date")
def format_date(value, format="%d %B %Y, %I:%M %p"):
    if value is None:
        return ""
    return datetime(*value[:6]).strftime(format)


@app.route("/")
def index():
    start_time = time.time()
    feeds = Feed.query.all()
    num_failed = 0
    all_items = []
    for feed in feeds:
        try:
            parsed_feed = feedparser.parse(feed.url)
            feed_pub_date = parsed_feed.feed.get("published_parsed", time.localtime())
            for entry in parsed_feed.entries:
                all_items.append(
                    {
                        "feed_name": parsed_feed.feed.title,
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published_parsed", feed_pub_date),
                        "description": entry.description,
                        "author": entry.get("author", None),
                    }
                )
        except Exception as e:
            print(f"failed to load feed {feed}: {e}")
            num_failed += 1
    all_items.sort(key=lambda x: x["published"], reverse=True)
    end_time = time.time()
    return render_template(
        "index.html",
        items=all_items[:100],
        fetch_time=round(end_time - start_time, 3),
        feed_count=len(feeds),
        item_count=len(all_items),
        failed_feed_count=num_failed,
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
