# Database Schema Complete Columns Fix - 2025-10-24

## Additional Issues Fixed
After initial table creation, discovered missing columns causing new errors:
- `no such column: sort_order` in indicator_categories
- `no such column: is_active` in indicator table
- `no such table: trend_alert_config`

## Complete Column List Added

### indicator_categories table
Added columns:
- `sort_order INTEGER DEFAULT 0` - 排序字段
- `is_active INTEGER DEFAULT 1` - 激活状态

### indicator table
Added columns:
- `is_active INTEGER DEFAULT 1` - 激活状态

### indicator_parameters table
Updated column names and added:
- `param_type` (renamed from `type`) - 参数类型
- `step_value` (renamed from `step`) - 步进值
- `is_required INTEGER DEFAULT 1` - 是否必需
- `sort_order INTEGER DEFAULT 0` - 排序

### indicator_implementations table
Updated column names and added:
- `implementation_code` (renamed from `code`) - 实现代码
- `priority INTEGER DEFAULT 50` - 优先级
- `performance_score REAL DEFAULT 1.0` - 性能评分
- `is_active INTEGER DEFAULT 1` - 激活状态

### trend_alert_config table
New table for trend analysis alerts:
- `id, config_key, config_value, is_active, created_at, updated_at`

## Technical Notes
Column names and types now match exactly what the code queries expect. All fields have appropriate default values to ensure backward compatibility.
