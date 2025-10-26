# Distributed Service Registration Fix - 2025-10-24

## Problem
The distributed service monitor in the menu bar was failing with:
```
ValueError: Service with name 'distributed_service' is not registered
```

## Root Cause Analysis
In `core/services/service_bootstrap.py` line 917, the code was calling:
```python
self.service_container.register_alias('distributed_service', DistributedService)
```

However, the `register_alias` method **does not exist** in `ServiceContainer`. This was a coding error.

## Solution
Changed the registration to use the proper `name` parameter in the `register_factory` method:
```python
# Old (incorrect):
self.service_container.register_alias('distributed_service', DistributedService)

# New (correct):
self.service_container.register_factory(
    DistributedService,
    create_distributed_service,
    scope=ServiceScope.SINGLETON,
    name='distributed_service'
)
```

## Technical Details
- The `ServiceContainer.get(name)` method calls `resolve_by_name(name)` internally
- `resolve_by_name` looks up services registered with a `name` parameter
- The correct way to register with both type and name is to call `register_factory` twice or use the `name` parameter

## Files Modified
- `core/services/service_bootstrap.py` (lines 916-924)

## Verification
After this fix, `container.get('distributed_service')` will correctly resolve to the DistributedService instance.
