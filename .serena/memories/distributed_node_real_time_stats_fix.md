# Distributed Node Real-Time Statistics Fix - 2025-10-24

## Problems Identified
From the screenshot, the distributed node monitor showed:
1. CPU usage always 0.0%
2. Memory usage always 0.0%  
3. Current tasks always 0
4. Uptime always 0秒

## Root Causes

### 1. Static Initial Values
When nodes are added via `add_node()`, they're initialized with static values:
```python
cpu_usage=0.0,
memory_usage=0.0, 
task_count=0
```
These values were **never updated** after initialization.

### 2. Missing Uptime Tracking
NodeInfo class didn't have a `created_at` field to track when the node was added, making uptime calculation impossible.

### 3. No Real-Time Updates
The `get_all_nodes_status()` method simply returned the static values without fetching real data from nodes.

## Solutions Implemented

### 1. Added created_at Field to NodeInfo
**File**: `core/services/distributed_service.py` (lines 52-58)

```python
@dataclass
class NodeInfo:
    ...
    created_at: Optional[datetime] = None  # 节点创建时间
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
```

### 2. Implemented _update_node_stats() Method
**File**: `core/services/distributed_service.py` (lines 357-406)

This method attempts to fetch real-time data using a three-tier strategy:

**Tier 1**: HTTP API Call
- Tries to GET `/api/v1/status` from the node
- Updates cpu_usage, memory_usage, task_count from response
- Updates status to 'active' and last_heartbeat

**Tier 2**: Local System Stats (for 127.0.0.1/localhost)
- Uses `psutil` to get real CPU and memory usage
- Counts tasks assigned to this node
- Only for local nodes (demonstration/testing)

**Tier 3**: Offline Handling
- Sets all stats to 0 for offline nodes
- Preserves existing values for unreachable remote nodes

### 3. Enhanced get_all_nodes_status()
**File**: `core/services/distributed_service.py` (lines 321-355)

**Uptime Calculation**:
```python
# Use created_at for accurate uptime
if hasattr(node, 'created_at') and node.created_at:
    uptime_seconds = (datetime.now() - node.created_at).total_seconds()
else:
    # Fallback to last_heartbeat
    uptime_seconds = (datetime.now() - node.last_heartbeat).total_seconds()
```

**Real-Time Updates**:
```python
# Update stats before returning
self._update_node_stats(node_id)
```

## Data Flow

### Refresh Cycle (Every 5 seconds):
1. UI Timer triggers `refresh_nodes()`
2. Calls `distributed_service.get_all_nodes_status()`
3. For each node:
   - Calculate uptime from `created_at`
   - Call `_update_node_stats(node_id)`
   - Try HTTP call to get real stats
   - Fallback to local psutil for localhost
   - Return updated values
4. UI updates table with fresh data

### Node Stats Priority:
1. **Real HTTP Response** (if node has API server)
2. **Local psutil Data** (for 127.0.0.1 nodes)
3. **Zero Values** (for offline nodes)
4. **Cached Values** (for unreachable remote nodes)

## Benefits

### For Local Testing:
- Shows real CPU/memory from local system
- Counts actual running tasks
- Displays accurate uptime

### For Remote Nodes:
- Fetches stats via HTTP API if available
- Marks offline nodes clearly (all 0s)
- Updates status dynamically

### For UI:
- Auto-refresh now shows changing values
- Uptime increases over time
- Status reflects actual connectivity

## Testing Recommendations
1. Add local node (127.0.0.1) → See real system stats
2. Add remote node → See connection status
3. Wait 5-10 seconds → Observe auto-refresh updating data
4. Stop a node → See stats go to 0 and status change to offline

## Files Modified
- `core/services/distributed_service.py` (NodeInfo class, get_all_nodes_status, new _update_node_stats)
