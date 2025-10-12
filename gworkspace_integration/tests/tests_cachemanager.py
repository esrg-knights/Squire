from threading import Thread
import time
from unittest.mock import Mock

from django.core.cache import cache
from django.test import TestCase

from gworkspace_integration.tests.util import CacheTestMixin
from gworkspace_integration.workspace import WorkspaceCacheManager


class WorkspaceCacheManagerTestCase(CacheTestMixin, TestCase):
    """Tests for caching behaviour"""

    def test_cache_set(self):
        """Tests if cache is set up and the API-function is not called unnecessarily"""

        expensive_fn = Mock(return_value="fn_result")
        res = WorkspaceCacheManager.fetch_with_lock(expensive_fn, "TEST_CACHE_KEY")

        # Result is provided and cache is written to
        expensive_fn.assert_called_once()
        self.assertEqual(res, "fn_result")
        self.assertEqual(cache.get("TEST_CACHE_KEY"), "fn_result")

        # Calling it a second time shouldn't yield another function call, but still yield the earlier result
        expensive_fn.reset_mock()
        res = WorkspaceCacheManager.fetch_with_lock(expensive_fn, "TEST_CACHE_KEY")
        expensive_fn.assert_not_called()
        self.assertEqual(res, "fn_result")

    def test_cache_lock(self):
        """Tests what happens when the cache is being refreshed by another process"""
        # Set cache key manually to imitate other process fetching cache results
        cache.set("TEST_CACHE_KEY_LCK", True)
        expensive_fn = Mock(return_value="fn_result")

        # Should timeout
        with self.assertRaises(TimeoutError):
            WorkspaceCacheManager.fetch_with_lock(
                expensive_fn, "TEST_CACHE_KEY", lock_key="TEST_CACHE_KEY_LCK", retries=0
            )

        # Should just yield the result if timeouts are disabled
        self.assertEqual(
            WorkspaceCacheManager.fetch_with_lock(
                expensive_fn, "TEST_CACHE_KEY", lock_key="TEST_CACHE_KEY_LCK", raise_timeout=False, retries=0
            ),
            "fn_result",
        )
        expensive_fn.assert_called_once()

        def _slow_set_cache():
            time.sleep(0.1)
            cache.set("TEST_CACHE_KEY", "slow_result")

        # Mimic another process already fetching the data. Should retrieve from cache
        expensive_fn.reset_mock()
        cache.set("TEST_CACHE_KEY_LCK", True)
        thread = Thread(target=_slow_set_cache)
        thread.start()

        self.assertEqual(
            WorkspaceCacheManager.fetch_with_lock(
                expensive_fn, "TEST_CACHE_KEY", lock_key="TEST_CACHE_KEY_LCK", retry_delay=0.2, retries=1
            ),
            "slow_result",
        )
        thread.join()
        expensive_fn.assert_not_called()
