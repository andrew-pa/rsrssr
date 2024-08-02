from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import feedparser
import time
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rss_feeds.db'
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

@app.template_filter('format_date')
def format_date(value, format='%d %B %Y, %I:%M %p'):
    if value is None:
        return ""
    return datetime(*value[:6]).strftime(format)

@app.route('/')
def index():
    start_time = time.time()
    feeds = Feed.query.all()
    all_items = []
    for feed in feeds:
        parsed_feed = feedparser.parse(feed.url)
        for entry in parsed_feed.entries:
            all_items.append({
                'feed_name': parsed_feed.feed.title,
                'title': entry.title,
                'link': entry.link,
                'published': entry.published_parsed
            })
    all_items.sort(key=lambda x: x['published'], reverse=True)
    end_time = time.time()
    return render_template('index.html', items=all_items[:200], fetch_time = round(end_time-start_time, 3), feed_count = len(feeds), item_count=len(all_items))

@app.route('/feeds', methods=['GET', 'POST'])
def manage_feeds():
    if request.method == 'POST':
        url = request.form['url']
        if 'delete' in request.form:
            feed = Feed.query.get(request.form['delete'])
            db.session.delete(feed)
        else:
            new_feed = Feed()
            new_feed.url = url
            db.session.add(new_feed)
        db.session.commit()
        return redirect(url_for('manage_feeds'))
    
    feeds = Feed.query.all()
    return render_template('feeds.html', feeds=feeds)

@app.route('/static/<path:path>')
def send_static(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    app.run(debug=True)
