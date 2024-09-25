import time
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io
import pandas as pd
import datetime

from logic import (
    add_feed,
    delete_feed,
    fetch_update_stats,
    item_list,
    overview,
    feed_list,
)
from stats_plot import plot_update_stats_figure
from update import update_feed
from models import Base, Item, Feed, UpdateStat

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rss_feeds.db"
db = SQLAlchemy(app)

with app.app_context():
    Base.metadata.create_all(bind=db.engine)


@app.template_filter("format_date")
def format_date(value, format="%d %B %Y, %I:%M %p"):
    if value is None:
        return None
    return value.strftime(format)


@app.route("/list")
def page_item_list():
    offset = request.args.get("offset", default=0, type=int)
    specific_feed_id = request.args.get("feed", default=None, type=int)

    props = item_list(db.session, offset, specific_feed_id)

    return render_template("index.html", **props)


@app.route("/")
def page_overview():
    props = overview(db.session)
    return render_template("overview.html", **props)


@app.route("/feeds", methods=["GET", "POST"])
def page_manage_feeds():
    if request.method == "POST":
        if "delete" in request.form:
            delete_feed(db.session, int(request.form["delete"]))
        else:
            add_feed(db.session, request.form["url"])
        return redirect(url_for("page_manage_feeds"))

    return render_template("feeds.html", **feed_list(db.session))


@app.route("/stats")
def graph_update_stats():
    timeframe = request.args.get("window", default="month", type=str)
    data = fetch_update_stats(db.session, timeframe)
    fig = plot_update_stats_figure(data)
    fig_html = plotly.io.to_html(fig, full_html=False)
    return render_template("stats.html", figure=fig_html)


@app.route("/static/<path:path>")
def send_static(path):
    return app.send_static_file(path)


if __name__ == "__main__":
    app.run(debug=True)
