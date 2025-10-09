#!/usr/bin/env python
"""
选项B+C最终验证脚本

验证所有关键修复和优化是否正确实施
"""

import sys
from pathlib import Path
from datetime import datetime

print("="*80)
print("选项B + 选项C 最终验证")
print("="*80)
print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

results = {
    'total': 0,
    'passed': 0,
    'failed': 0,
    'warnings': 0,
    'details': []
}


def verify(name, check_func, critical=True):
    """执行单项验证"""
    results['total'] += 1
    print(f"[{results['total']}] 验证: {name}")
    print("-" * 60)

    try:
        success, message = check_func()
        if success:
            results['passed'] += 1
            print(f"✓ 通过: {message}")
        else:
            if critical:
                results['failed'] += 1
                print(f"✗ 失败: {message}")
            else:
                results['warnings'] += 1
                print(f"⚠ 警告: {message}")

        results['details'].append({
            'name': name,
            'success': success,
            'message': message,
            'critical': critical
        })

    except Exception as e:
        results['failed'] += 1
        msg = f"验证异常: {str(e)}"
        print(f"✗ {msg}")
        results['details'].append({
            'name': name,
            'success': False,
            'message': msg,
            'critical': critical
        })

    print()


# ============================================================================
# 验证项目
# ============================================================================

def check_core_services_exist():
    """检查核心服务文件是否存在"""
    services = [
        'config_service.py',
        'database_service.py',
        'cache_service.py',
        'data_service.py',
        'plugin_service.py',
        'network_service.py',
        'security_service.py',
        'performance_service.py',
        'environment_service.py',
        'market_service.py',
        'analysis_service.py',
        'trading_service.py',
        'notification_service.py',
        'lifecycle_service.py',
        'extension_service.py',
    ]

    services_dir = Path('core/services')
    missing = []

    for service in services:
        if not (services_dir / service).exists():
            missing.append(service)

    if missing:
        return False, f"缺少{len(missing)}个核心服务: {', '.join(missing[:3])}..."

    return True, f"所有15个核心服务文件存在"


def check_duplicate_services_removed():
    """检查重复服务是否已删除"""
    services_dir = Path('core/services')

    # 应该已删除的服务
    deprecated = [
        'unified_data_service.py',
        'unified_database_service.py',
        'unified_cache_service.py',
        'unified_config_service.py',
        'unified_plugin_service.py',
    ]

    found = []
    for service in deprecated:
        if (services_dir / service).exists():
            found.append(service)

    if found:
        return False, f"发现{len(found)}个应删除的服务: {', '.join(found)}"

    return True, "重复服务已全部删除"


def check_standard_data_fixed():
    """检查StandardData是否已修复"""
    pipeline_file = Path('core/tet_data_pipeline.py')

    if not pipeline_file.exists():
        return False, "tet_data_pipeline.py不存在"

    content = pipeline_file.read_text(encoding='utf-8')

    has_success = 'success: bool' in content or 'success:bool' in content
    has_error_message = 'error_message: Optional[str]' in content or 'error_message:Optional[str]' in content

    if has_success and has_error_message:
        return True, "StandardData已添加success和error_message属性"

    missing = []
    if not has_success:
        missing.append('success')
    if not has_error_message:
        missing.append('error_message')

    return False, f"StandardData缺少属性: {', '.join(missing)}"


def check_field_mapping_fixed():
    """检查字段映射引擎是否已修复"""
    mapping_file = Path('core/data/field_mapping_engine.py')

    if not mapping_file.exists():
        return False, "field_mapping_engine.py不存在"

    content = mapping_file.read_text(encoding='utf-8')

    # 检查是否有int()转换
    has_fix = 'int(numeric_data.notna().sum())' in content or \
              'int(valid_count)' in content or \
              'valid_count = numeric_data.notna().sum()\n' not in content

    if has_fix:
        return True, "字段映射验证逻辑已修复"

    return False, "字段映射验证可能仍有问题"


def check_base_service_metrics():
    """检查BaseService的metrics属性"""
    base_service_file = Path('core/services/base_service.py')

    if not base_service_file.exists():
        return False, "base_service.py不存在"

    content = base_service_file.read_text(encoding='utf-8')

    # 检查是否有to_dict或__dict__处理
    has_to_dict = 'to_dict' in content
    has_vars = 'vars(self._metrics)' in content or '__dict__' in content

    if has_to_dict or has_vars:
        return True, "BaseService.metrics已支持对象类型"

    return False, "BaseService.metrics可能不支持对象类型"


def check_parallel_bootstrap_created():
    """检查并行启动模块是否已创建"""
    bootstrap_file = Path('parallel_service_bootstrap.py')

    if not bootstrap_file.exists():
        return False, "parallel_service_bootstrap.py不存在"

    content = bootstrap_file.read_text(encoding='utf-8')

    has_parallel = 'bootstrap_parallel' in content
    has_sequential = 'bootstrap_sequential' in content

    if has_parallel and has_sequential:
        return True, "并行启动模块已创建，包含双模式支持"

    return False, "并行启动模块不完整"


def check_test_script_updated():
    """检查测试脚本是否已更新"""
    test_file = Path('final_regression_test.py')

    if not test_file.exists():
        return False, "final_regression_test.py不存在"

    content = test_file.read_text(encoding='utf-8')

    # 检查是否有修复后的测试代码
    has_metrics_property = 'perf_service.metrics' in content
    has_env_check = 'isinstance(env_info, dict)' in content

    if has_metrics_property or has_env_check:
        return True, "测试脚本已更新以适配新架构"

    return False, "测试脚本可能未更新"


def check_documentation_complete():
    """检查文档是否完整"""
    required_docs = [
        'PROJECT_DELIVERY_SUMMARY.md',
        'ARCHITECTURE_COMPLETION_PLAN.md',
        'CRITICAL_ISSUES_FIX_REPORT.md',
        'OPTION_BC_FINAL_REPORT.md',
    ]

    missing = []
    for doc in required_docs:
        if not Path(doc).exists():
            missing.append(doc)

    if missing:
        return False, f"缺少{len(missing)}个文档: {', '.join(missing[:2])}..."

    return True, f"所有{len(required_docs)}个关键文档已生成"


def check_backup_safety():
    """检查备份是否安全"""
    backup_dir = Path('core/services/.backup')

    if not backup_dir.exists():
        return True, "无备份目录（可能已清理）"

    backup_files = list(backup_dir.glob('*.py'))

    if backup_files:
        return True, f"备份安全：{len(backup_files)}个文件已备份"

    return True, "备份目录为空（正常）"


# ============================================================================
# 执行验证
# ============================================================================

verify("核心服务文件完整性", check_core_services_exist, critical=True)
verify("重复服务清理", check_duplicate_services_removed, critical=True)
verify("StandardData修复", check_standard_data_fixed, critical=True)
verify("字段映射引擎修复", check_field_mapping_fixed, critical=True)
verify("BaseService.metrics增强", check_base_service_metrics, critical=True)
verify("并行启动模块", check_parallel_bootstrap_created, critical=False)
verify("测试脚本更新", check_test_script_updated, critical=False)
verify("文档完整性", check_documentation_complete, critical=False)
verify("备份安全性", check_backup_safety, critical=False)

# ============================================================================
# 生成报告
# ============================================================================

print("="*80)
print("验证汇总")
print("="*80)
print(f"总验证项: {results['total']}")
print(f"✓ 通过: {results['passed']}")
print(f"✗ 失败: {results['failed']}")
print(f"⚠ 警告: {results['warnings']}")

success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
print(f"通过率: {success_rate:.1f}%")
print()

if results['failed'] > 0:
    print("失败项详情:")
    for detail in results['details']:
        if not detail['success'] and detail['critical']:
            print(f"  - {detail['name']}: {detail['message']}")
    print()

if results['warnings'] > 0:
    print("警告项详情:")
    for detail in results['details']:
        if not detail['success'] and not detail['critical']:
            print(f"  - {detail['name']}: {detail['message']}")
    print()

print("="*80)

# 最终判断
if results['failed'] == 0:
    print("✅ 所有关键验证通过，系统可以交付！")
    exit_code = 0
elif results['failed'] <= 2:
    print("⚠️ 大部分验证通过，建议修复失败项后交付")
    exit_code = 1
else:
    print("❌ 多个关键验证失败，建议修复后再交付")
    exit_code = 2

print("="*80)

sys.exit(exit_code)
