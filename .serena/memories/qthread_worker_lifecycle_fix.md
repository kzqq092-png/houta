# QThread Worker Lifecycle Management Fix - 2025-10-24

## Problem
RuntimeError when accessing NodeStatsWorker after it was deleted:
```
RuntimeError: wrapped C/C++ object of type NodeStatsWorker has been deleted
```

Occurred at line 192: `if self.stats_worker and self.stats_worker.isRunning()`

## Root Cause

### Qt Object Lifecycle Issue
1. **Auto-deletion too early**: `deleteLater()` was called immediately in lambda
2. **Dangling reference**: Python still held reference to deleted C++ object
3. **Race condition**: Thread might finish and delete before next check

### The Problem Code
```python
self.stats_worker.finished.connect(lambda: self.stats_worker.deleteLater())
# Lambda executes immediately after thread finishes
# Next refresh_nodes call: isRunning() on deleted object → RuntimeError
```

## Solution

### 1. Proper Cleanup Sequence (lines 210-215)
```python
def _on_worker_finished(self):
    """工作线程完成回调"""
    if self.stats_worker:
        self.stats_worker.deleteLater()  # Schedule deletion
        self.stats_worker = None  # Clear reference immediately
```

**Benefits**:
- Clears Python reference before Qt deletes C++ object
- Prevents access to deleted object
- Clean separation of concerns

### 2. Safe State Check with Exception Handling (lines 189-208)
```python
def refresh_nodes(self):
    try:
        if self.stats_worker is not None:
            try:
                if self.stats_worker.isRunning():
                    return
            except RuntimeError:
                # Object deleted, clear reference
                self.stats_worker = None
        
        # Create new worker...
    except Exception as e:
        logger.error(f"刷新节点失败: {e}")
```

**Protection Layers**:
1. Check if worker exists (`is not None`)
2. Try to call `isRunning()` in try-except
3. Catch RuntimeError and clear reference
4. Outer try-except for any other errors

### 3. Safe Cleanup on Close (lines 445-459)
```python
def closeEvent(self, event):
    if self.stats_worker is not None:
        try:
            if self.stats_worker.isRunning():
                self.stats_worker.stop()
                self.stats_worker.wait(1000)
        except RuntimeError:
            pass  # Already deleted, ignore
```

## Qt Object Lifecycle Best Practices

### Problem Pattern (Don't Do This):
```python
# BAD: Lambda captures self reference
worker.finished.connect(lambda: worker.deleteLater())
# Python reference still exists after C++ deletion
```

### Correct Pattern (Do This):
```python
# GOOD: Proper callback that clears reference
def _on_finished(self):
    if self.worker:
        self.worker.deleteLater()
        self.worker = None  # Clear reference!

worker.finished.connect(self._on_finished)
```

### Safe Access Pattern:
```python
# GOOD: Check and handle RuntimeError
if self.worker is not None:
    try:
        if self.worker.isRunning():
            # Do something
    except RuntimeError:
        self.worker = None  # Clear dangling reference
```

## Key Lessons

### 1. Qt Object Deletion
- `deleteLater()` schedules deletion, doesn't delete immediately
- Python wrapper can outlive C++ object
- Must clear Python reference manually

### 2. Thread Lifecycle
- Thread may finish between check and use
- Always wrap Qt object access in try-except
- Use `is not None` before `isinstance()` or method calls

### 3. Signal-Slot Connections
- Avoid lambdas that capture object references
- Use proper callback methods
- Clean up references in callbacks

## Files Modified
- `gui/dialogs/distributed_node_monitor_dialog.py` (lines 189-215, 445-459)

## Testing Checklist
- ✅ No RuntimeError on rapid refresh
- ✅ No errors when adding nodes
- ✅ Clean dialog close
- ✅ No memory leaks
- ✅ Worker threads properly cleaned up
