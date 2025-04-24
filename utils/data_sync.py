"""
Data Synchronization Manager Module

This module provides classes for managing data synchronization.
"""

from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker, QWaitCondition

class DataSynchronizer(QObject):
    """Manages data synchronization between components"""
    
    data_updated = pyqtSignal(str, object)  # Signal emitted when data is updated
    sync_completed = pyqtSignal()  # Signal emitted when sync is complete
    
    def __init__(self):
        super().__init__()
        self.data_store = {}
        self.mutex = QMutex()
        self.sync_condition = QWaitCondition()
        self.sync_complete = False
        
    def set_data(self, key: str, value: Any):
        """Set data for a key"""
        with QMutexLocker(self.mutex):
            self.data_store[key] = value
            self.data_updated.emit(key, value)
            
    def get_data(self, key: str) -> Optional[Any]:
        """Get data for a key"""
        with QMutexLocker(self.mutex):
            return self.data_store.get(key)
            
    def wait_for_sync(self, timeout: int = 5000) -> bool:
        """Wait for synchronization to complete"""
        with QMutexLocker(self.mutex):
            if not self.sync_complete:
                return self.sync_condition.wait(self.mutex, timeout)
            return True
            
    def notify_sync_complete(self):
        """Notify that synchronization is complete"""
        with QMutexLocker(self.mutex):
            self.sync_complete = True
            self.sync_condition.wakeAll()
            self.sync_completed.emit()
            
    def clear_data(self):
        """Clear all synchronized data"""
        with QMutexLocker(self.mutex):
            self.data_store.clear()
            self.sync_complete = False
            
class SyncManager:
    """High-level manager for data synchronization"""
    
    def __init__(self):
        self.synchronizers: Dict[str, DataSynchronizer] = {}
        self.mutex = QMutex()
        
    def get_synchronizer(self, name: str) -> DataSynchronizer:
        """Get or create a synchronizer for a component"""
        with QMutexLocker(self.mutex):
            if name not in self.synchronizers:
                self.synchronizers[name] = DataSynchronizer()
            return self.synchronizers[name]
            
    def sync_data(self, source: str, target: str, key: str):
        """Synchronize data between components"""
        source_sync = self.get_synchronizer(source)
        target_sync = self.get_synchronizer(target)
        
        data = source_sync.get_data(key)
        if data is not None:
            target_sync.set_data(key, data)
            
    def wait_for_all(self, timeout: int = 5000) -> bool:
        """Wait for all synchronizers to complete"""
        with QMutexLocker(self.mutex):
            for synchronizer in self.synchronizers.values():
                if not synchronizer.wait_for_sync(timeout):
                    return False
            return True
            
    def clear_all(self):
        """Clear all synchronizers"""
        with QMutexLocker(self.mutex):
            for synchronizer in self.synchronizers.values():
                synchronizer.clear_data()
                
class SyncComponent:
    """Base class for components that need synchronization"""
    
    def __init__(self, sync_manager: SyncManager, name: str):
        self.sync_manager = sync_manager
        self.name = name
        self.synchronizer = sync_manager.get_synchronizer(name)
        
    def set_data(self, key: str, value: Any):
        """Set synchronized data"""
        self.synchronizer.set_data(key, value)
        
    def get_data(self, key: str) -> Optional[Any]:
        """Get synchronized data"""
        return self.synchronizer.get_data(key)
        
    def wait_for_sync(self, timeout: int = 5000) -> bool:
        """Wait for synchronization to complete"""
        return self.synchronizer.wait_for_sync(timeout)
        
    def notify_sync_complete(self):
        """Notify that synchronization is complete"""
        self.synchronizer.notify_sync_complete() 