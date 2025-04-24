"""
Enhanced Data Cache Module

This module provides a unified data caching solution that combines memory and disk caching
with expiration, thread safety, and LRU eviction.
"""

import os
import pickle
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from PyQt5.QtCore import QMutex, QMutexLocker

class DataCache:
    """Enhanced data cache that combines memory and disk caching with expiration and LRU eviction.
    
    Features:
    - Two-level caching (memory and disk)
    - Thread-safe operations
    - LRU eviction strategy
    - Data expiration
    - Automatic cleanup
    - Configurable serialization
    
    Args:
        max_memory_size (int): Maximum number of items in memory cache
        cache_dir (str): Directory for disk cache
        expire_minutes (int): Data expiration time in minutes
        cleanup_interval (int): Cleanup interval in minutes
        persist_by_default (bool): Whether to persist data to disk by default
    """
    
    def __init__(
        self,
        max_memory_size: int = 1000,
        cache_dir: str = ".cache",
        expire_minutes: int = 30,
        cleanup_interval: int = 5,
        persist_by_default: bool = True
    ):
        self.max_memory_size = max_memory_size
        self.cache_dir = cache_dir
        self.expire_minutes = expire_minutes
        self.cleanup_interval = cleanup_interval
        self.persist_by_default = persist_by_default
        
        # Initialize caches
        self._memory_cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        self._expiry_times: Dict[str, datetime] = {}
        
        # Initialize locks
        self._memory_mutex = QMutex()
        self._disk_mutex = threading.Lock()
        
        # Ensure cache directory exists
        self._ensure_cache_dir()
        
        # Start cleanup timer
        self._start_cleanup_timer()
        
    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _start_cleanup_timer(self):
        """Start the cleanup timer"""
        def cleanup():
            while True:
                time.sleep(self.cleanup_interval * 60)
                self._cleanup()
                
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
        
    def _cleanup(self):
        """Clean up expired items from both memory and disk cache"""
        now = datetime.now()
        
        # Clean memory cache
        with QMutexLocker(self._memory_mutex):
            expired_keys = [
                key for key, expiry in self._expiry_times.items()
                if expiry < now
            ]
            for key in expired_keys:
                self._remove_from_memory(key)
                
        # Clean disk cache
        with self._disk_mutex:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.cache'):
                    continue
                    
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'rb') as f:
                        metadata = pickle.load(f)
                        if metadata['expiry'] < now:
                            os.remove(filepath)
                except:
                    # Remove corrupted cache files
                    try:
                        os.remove(filepath)
                    except:
                        pass
                        
    def _get_cache_path(self, key: str) -> str:
        """Get file path for cached item"""
        return os.path.join(self.cache_dir, f"{key}.cache")
        
    def _remove_from_memory(self, key: str):
        """Remove an item from memory cache"""
        self._memory_cache.pop(key, None)
        self._access_times.pop(key, None)
        self._expiry_times.pop(key, None)
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        now = datetime.now()
        
        # Try memory cache first
        with QMutexLocker(self._memory_mutex):
            if key in self._memory_cache:
                if self._expiry_times[key] > now:
                    self._access_times[key] = time.time()
                    return self._memory_cache[key]
                else:
                    self._remove_from_memory(key)
                    
        # Try disk cache
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            with self._disk_mutex:
                try:
                    with open(cache_path, 'rb') as f:
                        metadata = pickle.load(f)
                        if metadata['expiry'] > now:
                            data = metadata['data']
                            # Add to memory cache if space available
                            with QMutexLocker(self._memory_mutex):
                                if len(self._memory_cache) < self.max_memory_size:
                                    self._memory_cache[key] = data
                                    self._access_times[key] = time.time()
                                    self._expiry_times[key] = metadata['expiry']
                            return data
                except:
                    pass
                    
        return None
        
    def set(
        self,
        key: str,
        value: Any,
        expire_minutes: Optional[int] = None,
        persist: Optional[bool] = None
    ):
        """Set item in cache
        
        Args:
            key: Cache key
            value: Value to cache
            expire_minutes: Optional custom expiration time in minutes
            persist: Whether to persist to disk, defaults to persist_by_default
        """
        if expire_minutes is None:
            expire_minutes = self.expire_minutes
            
        if persist is None:
            persist = self.persist_by_default
            
        expiry = datetime.now() + timedelta(minutes=expire_minutes)
        
        # Update memory cache
        with QMutexLocker(self._memory_mutex):
            if len(self._memory_cache) >= self.max_memory_size:
                # Remove least recently used item
                lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
                self._remove_from_memory(lru_key)
                
            self._memory_cache[key] = value
            self._access_times[key] = time.time()
            self._expiry_times[key] = expiry
            
        # Update disk cache if requested
        if persist:
            cache_path = self._get_cache_path(key)
            with self._disk_mutex:
                try:
                    metadata = {
                        'data': value,
                        'expiry': expiry
                    }
                    with open(cache_path, 'wb') as f:
                        pickle.dump(metadata, f)
                except:
                    pass
                    
    def clear(self):
        """Clear all caches"""
        # Clear memory cache
        with QMutexLocker(self._memory_mutex):
            self._memory_cache.clear()
            self._access_times.clear()
            self._expiry_times.clear()
            
        # Clear disk cache
        with self._disk_mutex:
            for file in os.listdir(self.cache_dir):
                if file.endswith('.cache'):
                    try:
                        os.remove(os.path.join(self.cache_dir, file))
                    except:
                        pass
                        
    def remove(self, key: str):
        """Remove item from cache
        
        Args:
            key: Cache key to remove
        """
        # Remove from memory cache
        with QMutexLocker(self._memory_mutex):
            self._remove_from_memory(key)
            
        # Remove from disk cache
        cache_path = self._get_cache_path(key)
        with self._disk_mutex:
            try:
                if os.path.exists(cache_path):
                    os.remove(cache_path)
            except:
                pass
                
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics
        
        Returns:
            Dictionary containing cache statistics
        """
        with QMutexLocker(self._memory_mutex):
            memory_size = len(self._memory_cache)
            
        disk_size = len([f for f in os.listdir(self.cache_dir) if f.endswith('.cache')])
        
        return {
            'memory_size': memory_size,
            'disk_size': disk_size,
            'max_memory_size': self.max_memory_size
        } 