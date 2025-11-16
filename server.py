from urllib.parse import urlencode, urlunparse
from flask import (
    Flask,
    Request,
    abort,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
import plotly.io
import datetime
from config import database_uri

from logic import (
    add_feed,
    delete_feed,
    fetch_update_stats,
    item_list,
    overview,
    feed_list,
    record_visit,
    toggle_feed_downrank,
    update_feed_title,
    toggle_like,
    record_dismiss,
    unvisited_items_after,
)
from stats_plot import plot_update_stats_figure
from models import Base
from models import Item
from sqlalchemy import text

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
db = SQLAlchemy(app)

with app.app_context():
    Base.metadata.create_all(bind=db.engine)
    # Migrate: add dismissed column if it doesn't exist
    with db.engine.connect() as conn:
        existing = conn.execute(text("PRAGMA table_info('item')")).mappings().all()
        if not any(row["name"] == "dismissed" for row in existing):
            conn.execute(text("ALTER TABLE item ADD COLUMN dismissed DATETIME"))


@app.template_filter("format_date")
def format_date(value, format="%d %B %Y, %I:%M %p"):
    if value is None:
        return None
    return value.strftime(format)


@app.template_filter("update_query")
def update_query(request: Request, key: str, value):
    new_args = request.args.copy()
    if value is None:
        new_args.pop(key)
    else:
        new_args[key] = value
    new_query = urlencode(new_args, doseq=True)
    return f"{request.path}?{new_query}"


@app.route("/")
def page_overview():
    props = overview(db.session)
    return render_template("overview.html", **props)


@app.route("/list")
def page_item_list():
    offset = request.args.get("offset", default=0, type=int)
    specific_feed_id = request.args.get("feed", default=None, type=int)
    item_state = request.args.get("k", default="all", type=str)
    if item_state not in ("all", "visited", "liked"):
        abort(400)

    props = item_list(db.session, item_state, offset, specific_feed_id)

    return render_template("index.html", **props, request=request)


@app.route("/feeds", methods=["GET", "POST"])
def page_manage_feeds():
    if request.method == "POST":
        if "delete" in request.form:
            delete_feed(db.session, int(request.form["delete"]))
        elif "downrank" in request.form:
            toggle_feed_downrank(db.session, int(request.form["downrank"]))
        elif "feed_id" in request.form:
            update_feed_title(
                db.session,
                int(request.form["feed_id"]),
                request.form.get("title", ""),
            )
        else:
            add_feed(db.session, request.form["url"])
        return redirect(url_for("page_manage_feeds"))

    return render_template("feeds.html", **feed_list(db.session))


@app.route("/visit", methods=["POST"])
def visit_item():
    item_id = request.args.get("id", type=int)
    if not item_id:
        abort(400)
    record_visit(db.session, item_id)
    return ""


@app.route("/like", methods=["POST"])
def like_item():
    item_id = request.args.get("id", type=int)
    if not item_id:
        abort(400)
    toggle_like(db.session, item_id)
    print(request.referrer)
    return redirect(request.referrer or "/")


@app.route("/dismiss", methods=["POST"])
def dismiss_item():
    """
    API endpoint to mark an item as dismissed.
    """
    item_id = request.args.get("id", type=int)
    if not item_id:
        abort(400)
    record_dismiss(db.session, item_id)
    return redirect(request.referrer or "/")


@app.route("/api/unvisited")
def api_unvisited_items():
    """Return unvisited and not dismissed items newer than a given date."""
    date_str = request.args.get("after")
    if not date_str:
        abort(400)
    try:
        since_date = datetime.datetime.fromisoformat(date_str)
    except ValueError:
        abort(400)

    items = unvisited_items_after(db.session, since_date)

    return jsonify(
        [
            {
                "id": item.id,
                "url": item.link,
                "feedName": item.feed.title,
                "published": item.published.isoformat(),
            }
            for item in items
        ]
    )


@app.route("/stats")
def graph_update_stats():
    timeframe = request.args.get("window", default="week", type=str)
    data = fetch_update_stats(db.session, timeframe)
    fig = plot_update_stats_figure(data)
    fig_html = plotly.io.to_html(fig, full_html=False, default_height="80vh")
    return render_template("stats.html", figure=fig_html)


@app.route("/static/<path:path>")
def send_static(path):
    return app.send_static_file(path)


@app.route("/go/<int:item_id>")
def go_to_item(item_id: int):
    item = db.session.query(Item).get(item_id)
    if not item:
        abort(404)
    record_visit(db.session, item_id)
    return redirect(item.link)


if __name__ == "__main__":
    app.run(debug=True)
