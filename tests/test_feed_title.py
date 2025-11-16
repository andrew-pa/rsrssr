import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Feed

os.makedirs("instance", exist_ok=True)

from logic import update_feed_title


class UpdateFeedTitleTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        feed = Feed(url="http://example.com", title="Original Title")
        self.session.add(feed)
        self.session.commit()
        self.feed_id = feed.id
        self.engine = engine

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_updates_title_and_trims_whitespace(self):
        update_feed_title(self.session, self.feed_id, "  Updated Title  ")
        self.session.expire_all()
        updated = self.session.query(Feed).get(self.feed_id)
        self.assertEqual(updated.title, "Updated Title")

    def test_blank_title_clears_value(self):
        update_feed_title(self.session, self.feed_id, "   ")
        self.session.expire_all()
        updated = self.session.query(Feed).get(self.feed_id)
        self.assertIsNone(updated.title)


if __name__ == "__main__":
    unittest.main()
