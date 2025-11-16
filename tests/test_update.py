import os
import time
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Feed
from update import update_feeds


class TestUpdateFeedsConcurrency(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmpdir.name, "test.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _create_feed(self, session, url):
        feed = Feed(url=url)
        session.add(feed)
        session.commit()
        return feed

    def test_update_feeds_processes_feeds_concurrently(self):
        session = self.Session()
        self._create_feed(session, "https://example.com/one")
        self._create_feed(session, "https://example.com/two")

        def slow_update(worker_session, feed):
            time.sleep(0.25)
            return {
                "id": feed.id,
                "num_new_items": 1,
                "dur": 100,
                "cache_miss": True,
            }

        start = time.monotonic()
        stats = update_feeds(session, update_fn=slow_update, max_workers=2)
        elapsed = time.monotonic() - start

        self.assertLess(
            elapsed,
            0.45,
            msg=f"feeds should be processed concurrently, took {elapsed:.3f}s",
        )
        self.assertEqual(stats.num_fetched, 2)
        self.assertEqual(stats.num_updated, 2)

    def test_update_feeds_records_failures_without_aborting(self):
        session = self.Session()
        self._create_feed(session, "https://example.com/succeeds")
        self._create_feed(session, "https://example.com/fails")

        def conditional_update(worker_session, feed):
            if feed.url.endswith("fails"):
                raise ValueError("boom")
            return {
                "id": feed.id,
                "num_new_items": 2,
                "dur": 50,
                "cache_miss": True,
            }

        stats = update_feeds(session, update_fn=conditional_update, max_workers=2)

        self.assertEqual(stats.num_fetched, 1)
        self.assertEqual(stats.num_updated, 1)
        self.assertEqual(stats.num_failed, 1)


if __name__ == "__main__":
    unittest.main()
