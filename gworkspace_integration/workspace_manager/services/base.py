from collections.abc import Callable
import crypt
import logging
import re
from secrets import token_urlsafe
import time
from typing import Generic, TypeVar

from django.core.cache import cache
from django.utils.text import slugify

from gworkspace_integration.api.base import GoogleAPIService
from gworkspace_integration.api.client import GoogleWorkspaceSettings

T = TypeVar("T")


class APICacheHelper:
    """
    Helper class to reduce the number of expensive API calls through a (shared) cache.
    Requires Memcached to be setup to properly share the cache between multiple
    (Gunicorn) processes.
    """

    LOCK_TIMEOUT = 30  # seconds

    @classmethod
    def invalidate_cache(cls, cache_key: str):
        """Invalidates the given cache key"""
        cache.delete(cache_key)

    @classmethod
    def fetch_with_lock(
        cls,
        api_fn: Callable[[], T],
        cache_key: str,
        cache_timeout=3600,
        lock_key: str | None = None,
        retries: int = 5,
        retry_delay: float = 0.5,
        raise_timeout=True,
    ) -> T:
        """
        Fetch data from an API and add it to a cache. Subsequent calls with the same cache key
        will retrieve from the cache instead. Use this to reduce the number of API calls.
        If the data is not in cache, fetch the data from the API and lock.

        :param api_fn: function to rebuild the value if missing.
        :param cache_key: key to store/retrieve the cached value
        :param cache_timeout: TTL for cached value
        :param lock_key: optional lock key (defaults to cache_key + "_lock")
        :param retries: how many times to wait if another process is already refilling the cache
        :param retry_delay: delay between retries (in seconds)
        :param raise_timeout: whether to raise an exception on timeout or call `fetch_func` anyway

        :raise TimeoutError: if all the following conditions are met:

        - `raise_timeout=True`
        - the value was not present in the cache
        - another process is already calling `fetch_func` to retrieve from the cache
        - this other process is taking too long to do so (longer than `retries * retry_delay` seconds)
        """
        lock_key = lock_key or f"{cache_key}_lock"

        # Try to read from cache first
        data = cache.get(cache_key)
        if data is not None:
            return data

        # Avoid race conditions and acquire a lock. add(..) is atomic
        if cache.add(lock_key, True, timeout=cls.LOCK_TIMEOUT):
            try:
                # Call function and add to cache
                data = api_fn()
                cache.set(cache_key, data, timeout=cache_timeout)
                return data
            finally:
                # Release lock
                cache.delete(lock_key)
        else:
            # Another process is currently fetching the data
            for _ in range(retries):
                time.sleep(retry_delay)
                data = cache.get(cache_key)
                if data is not None:
                    return data
            # Took too long!
            if raise_timeout:
                raise TimeoutError(
                    f"Unable to retrieve workspace user list from cache. Another process was updating it but took too long!"
                )
            return api_fn()


T = TypeVar("T", bound=GoogleAPIService)


class SquireWorkspaceServiceBase(Generic[T], APICacheHelper):
    """Base class for a Squire service that interacts with various Google Services"""

    def __init__(self, service: T, settings: GoogleWorkspaceSettings):
        self._gservice = service
        self.settings = settings
        self.logger = logging.getLogger(f"squire_gworkspace.{self.__class__.__name__}")
