import time
import logging

from django.db import OperationalError

logger = logging.getLogger('salestracker.db')


def retry_on_db_locked(max_retries=5, base_delay=0.5):
    """Decorator que reintentar cuando SQLite dice 'database is locked'."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if 'database is locked' not in str(e):
                        raise
                    last_exc = e
                    wait = base_delay * (attempt + 1)
                    logger.warning('DB locked, retry %d/%d in %.1fs', attempt + 1, max_retries, wait)
                    time.sleep(wait)
            raise last_exc
        return wrapper
    return decorator
