"""LFU (Least Frequently Used) cache implementation."""

from typing import Dict, Optional, Any
from collections import defaultdict


class LFUCache:
    """
    LFU cache with size limit.
    
    Evicts least frequently used items when cache is full.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize LFU cache.
        
        Args:
            max_size: Maximum number of items in cache
        """
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.frequencies: Dict[str, int] = defaultdict(int)
        self.access_order: Dict[int, list] = defaultdict(list)
        self.min_freq = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache and update frequency.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key not in self.cache:
            return None
        
        # Update frequency
        old_freq = self.frequencies[key]
        self.frequencies[key] += 1
        new_freq = self.frequencies[key]
        
        # Remove from old frequency list
        if key in self.access_order[old_freq]:
            self.access_order[old_freq].remove(key)
            if not self.access_order[old_freq] and old_freq == self.min_freq:
                self.min_freq += 1
        
        # Add to new frequency list
        self.access_order[new_freq].append(key)
        
        return self.cache[key]
    
    def put(self, key: str, value: Any):
        """
        Add or update item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing item
            self.cache[key] = value
            self.get(key)  # Update frequency
            return
        
        # Check if we need to evict
        if len(self.cache) >= self.max_size:
            self._evict()
        
        # Add new item
        self.cache[key] = value
        self.frequencies[key] = 1
        self.min_freq = 1
        self.access_order[1].append(key)
    
    def _evict(self):
        """Evict least frequently used item."""
        # Get least frequently used items
        lfu_items = self.access_order[self.min_freq]
        
        if lfu_items:
            # Remove first item (FIFO among same frequency)
            evict_key = lfu_items.pop(0)
            del self.cache[evict_key]
            del self.frequencies[evict_key]
            
            # Update min_freq if needed
            if not lfu_items:
                # Find next minimum frequency
                while self.min_freq not in self.access_order or not self.access_order[self.min_freq]:
                    self.min_freq += 1
    
    def clear(self):
        """Clear all items from cache."""
        self.cache.clear()
        self.frequencies.clear()
        self.access_order.clear()
        self.min_freq = 0
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)
    
    def contains(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache

