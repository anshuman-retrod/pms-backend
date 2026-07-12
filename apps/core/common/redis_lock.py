import time
import logging
import uuid
from contextlib import contextmanager
from django.core.cache import cache

logger = logging.getLogger(__name__)

@contextmanager
def redis_distributed_lock(lock_key, timeout=15, retry_delay=0.1, max_retries=100):
    """
    A distributed lock context manager using Django's cache framework (Redis).
    Ensures safe concurrent operations for critical resources (e.g. room assignments).
    If Redis fails, it gracefully falls back (yielding acquired=False), letting DB transactions handle it.
    """
    acquired = False
    lock_value = str(uuid.uuid4())
    
    retries = 0
    while retries < max_retries:
        try:
            # cache.add uses SETNX atomically
            if cache.add(lock_key, lock_value, timeout):
                acquired = True
                break
        except Exception as e:
            logger.warning(f"Redis connection issue during lock acquisition: {e}. Falling back to DB-level safety.")
            break
            
        time.sleep(retry_delay)
        retries += 1
        
    try:
        yield acquired
    finally:
        if acquired:
            try:
                # Ensure we only delete our own lock
                if cache.get(lock_key) == lock_value:
                    cache.delete(lock_key)
            except Exception as e:
                logger.warning(f"Failed to release Redis lock for key {lock_key}: {e}")
