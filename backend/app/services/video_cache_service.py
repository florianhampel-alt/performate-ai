"""
Video Cache Service with TTL and Memory Management
Replaces the global video_storage dict to prevent memory leaks
"""

import time
import threading
from typing import Dict, Any, Optional
from collections import OrderedDict
from app.utils.logger import get_logger

logger = get_logger(__name__)

class VideoCache:
    """Thread-safe video cache with TTL and size limits"""
    
    def __init__(self, max_size: int = 50, ttl_seconds: int = 3600):
        """
        Args:
            max_size: Maximum number of videos to cache
            ttl_seconds: Time to live for cache entries (default 1 hour)
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        
        logger.info(f"VideoCache initialized: max_size={max_size}, ttl={ttl_seconds}s")
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Store video data with timestamp"""
        with self._lock:
            # Remove expired entries
            self._cleanup_expired()
            
            # Remove oldest if at capacity  
            if len(self.cache) >= self.max_size:
                oldest_key, oldest_value = self.cache.popitem(last=False)
                size_mb = oldest_value.get('size', 0) / (1024 * 1024)
                logger.warning(f"Evicted oldest video from cache: {oldest_key} ({size_mb:.1f}MB)")
                
            # Store with timestamp
            value['_timestamp'] = time.time()
            value['_access_count'] = value.get('_access_count', 0) + 1
            self.cache[key] = value
            
            size_mb = value.get('size', 0) / (1024 * 1024)
            logger.info(f"Cached video: {key} ({size_mb:.1f}MB), cache size: {len(self.cache)}/{self.max_size}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve video data if not expired"""
        with self._lock:
            if key not in self.cache:
                return None
                
            entry = self.cache[key]
            current_time = time.time()
            
            # Check if expired
            if current_time - entry.get('_timestamp', 0) > self.ttl_seconds:
                logger.info(f"Cache entry expired: {key}")
                del self.cache[key]
                return None
            
            # Update access stats and move to end (LRU)
            entry['_access_count'] = entry.get('_access_count', 0) + 1
            entry['_last_accessed'] = current_time
            self.cache.move_to_end(key)
            
            return entry
    
    def delete(self, key: str) -> bool:
        """Remove entry from cache"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                logger.info(f"Removed from cache: {key}")
                return True
            return False
    
    def clear(self) -> int:
        """Clear all cache entries"""
        with self._lock:
            count = len(self.cache)
            self.cache.clear()
            logger.warning(f"Cleared all cache entries: {count} videos removed")
            return count
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries (called with lock held)"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if current_time - value.get('_timestamp', 0) > self.ttl_seconds
        ]
        
        for key in expired_keys:
            size_mb = self.cache[key].get('size', 0) / (1024 * 1024)
            del self.cache[key]
            logger.info(f"Expired video removed from cache: {key} ({size_mb:.1f}MB)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            self._cleanup_expired()
            
            total_size = sum(entry.get('size', 0) for entry in self.cache.values())
            
            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "total_size_mb": total_size / (1024 * 1024),
                "ttl_seconds": self.ttl_seconds,
                "entries": [
                    {
                        "key": key,
                        "size_mb": entry.get('size', 0) / (1024 * 1024),
                        "storage_type": entry.get('storage_type', 'unknown'),
                        "age_seconds": int(time.time() - entry.get('_timestamp', 0)),
                        "access_count": entry.get('_access_count', 0)
                    }
                    for key, entry in self.cache.items()
                ]
            }
    
    def keys(self) -> list:
        """Get all cache keys"""
        with self._lock:
            self._cleanup_expired()
            return list(self.cache.keys())
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key) is not None
    
    def __len__(self) -> int:
        """Get number of non-expired entries"""
        with self._lock:
            self._cleanup_expired()
            return len(self.cache)

# Global video cache instance
video_cache = VideoCache(
    max_size=50,      # Maximum 50 videos in cache
    ttl_seconds=3600  # 1 hour TTL
)