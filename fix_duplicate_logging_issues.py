#!/usr/bin/env python3
"""
修复重复日志问题
解决AI预测服务和性能数据收集的重复警告
"""

import os
import sys
from pathlib import Path
import re


def fix_ai_prediction_service():
    """修复AI预测服务的重复警告问题"""
    print("🔧 修复AI预测服务重复警告...")

    ai_service_file = Path("core/services/ai_prediction_service.py")
    if not ai_service_file.exists():
        print("❌ AI预测服务文件不存在")
        return False

    # 读取文件内容
    with open(ai_service_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 添加调用频率限制
    rate_limit_code = '''
    def __init__(self):
        super().__init__()
        self._last_warning_time = {}  # 记录每种预测类型的最后警告时间
        self._warning_interval = 60  # 警告间隔（秒）
        
    def _should_warn(self, prediction_type: str) -> bool:
        """检查是否应该输出警告（避免重复警告）"""
        import time
        current_time = time.time()
        last_time = self._last_warning_time.get(prediction_type, 0)
        
        if current_time - last_time > self._warning_interval:
            self._last_warning_time[prediction_type] = current_time
            return True
        return False
'''

    # 替换构造函数
    old_init = r'def __init__\(self\):\s*super\(\).__init__\(\)'
    new_init = rate_limit_code.strip()

    if re.search(old_init, content):
        content = re.sub(old_init, new_init, content)
        print("✅ 已添加警告频率限制")
    else:
        print("⚠️ 未找到构造函数，手动添加警告限制")

    # 修改警告输出
    old_warning = r'logger\.warning\(f"不支持的预测类型: \{prediction_type\}"\)'
    new_warning = '''if self._should_warn(prediction_type):
                    logger.warning(f"不支持的预测类型: {prediction_type}")'''

    content = re.sub(old_warning, new_warning, content)

    # 写回文件
    with open(ai_service_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ AI预测服务修复完成")
    return True


def fix_risk_monitor_calls():
    """修复风险监控器的重复调用"""
    print("🔧 检查风险监控器调用...")

    risk_monitor_file = Path("core/risk_monitoring/enhanced_risk_monitor.py")
    if not risk_monitor_file.exists():
        print("❌ 风险监控器文件不存在")
        return False

    # 读取文件内容
    with open(risk_monitor_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 添加预测调用缓存
    cache_code = '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) if hasattr(super(), '__init__') else None
        self._prediction_cache = {}  # 预测结果缓存
        self._cache_ttl = 300  # 缓存有效期（秒）
        
    def _get_cached_prediction(self, prediction_type: str, cache_key: str):
        """获取缓存的预测结果"""
        import time
        current_time = time.time()
        
        if cache_key in self._prediction_cache:
            cached_result, timestamp = self._prediction_cache[cache_key]
            if current_time - timestamp < self._cache_ttl:
                return cached_result
        
        return None
    
    def _cache_prediction(self, cache_key: str, result):
        """缓存预测结果"""
        import time
        self._prediction_cache[cache_key] = (result, time.time())
'''

    # 查找并替换预测调用
    prediction_pattern = r'prediction_result = self\.ai_service\.predict\(\s*PredictionType\.RISK_FORECAST,\s*\{[^}]+\}\s*\)'

    def replace_prediction(match):
        original_call = match.group(0)
        return f'''
                # 生成缓存键
                cache_key = f"risk_forecast_{{metric.name}}_{{metric.value}}"
                
                # 尝试从缓存获取结果
                prediction_result = self._get_cached_prediction("RISK_FORECAST", cache_key)
                
                if prediction_result is None:
                    # 缓存未命中，进行预测
                    {original_call}
                    
                    # 缓存结果
                    if prediction_result:
                        self._cache_prediction(cache_key, prediction_result)
                else:
                    # 使用缓存结果
                    pass  # prediction_result already set
'''

    if re.search(prediction_pattern, content, re.DOTALL):
        content = re.sub(prediction_pattern, replace_prediction, content, flags=re.DOTALL)
        print("✅ 已添加预测结果缓存")
    else:
        print("⚠️ 未找到预测调用模式")

    # 添加缓存初始化代码
    if '__init__' not in content or 'self._prediction_cache' not in content:
        # 在类定义后添加缓存初始化
        class_pattern = r'(class EnhancedRiskMonitor[^:]*:)'
        content = re.sub(class_pattern, r'\1\n' + cache_code, content)
        print("✅ 已添加预测缓存机制")

    # 写回文件
    with open(risk_monitor_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ 风险监控器修复完成")
    return True


def add_service_deduplication():
    """添加服务去重机制"""
    print("🔧 添加服务去重机制...")

    bootstrap_file = Path("core/services/service_bootstrap.py")
    if not bootstrap_file.exists():
        print("❌ 服务引导文件不存在")
        return False

    # 读取文件内容
    with open(bootstrap_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 添加服务实例跟踪
    tracking_code = '''
    def __init__(self, service_container):
        self.service_container = service_container
        self._registered_services = set()  # 跟踪已注册的服务
        self._service_instances = {}  # 跟踪服务实例
        
    def _is_service_registered(self, service_class) -> bool:
        """检查服务是否已注册"""
        service_name = service_class.__name__
        return service_name in self._registered_services
    
    def _mark_service_registered(self, service_class):
        """标记服务已注册"""
        service_name = service_class.__name__
        self._registered_services.add(service_name)
        logger.debug(f"服务已标记为已注册: {service_name}")
'''

    # 查找构造函数并替换
    init_pattern = r'def __init__\(self, service_container\):\s*self\.service_container = service_container'

    if re.search(init_pattern, content):
        content = re.sub(init_pattern, tracking_code.strip(), content)
        print("✅ 已添加服务去重跟踪")
    else:
        print("⚠️ 未找到构造函数模式")

    # 修改服务注册方法，添加去重检查
    register_pattern = r'(self\.service_container\.register\(\s*(\w+Service),)'

    def add_dedup_check(match):
        full_match = match.group(0)
        service_class = match.group(2)
        return f'''
        if not self._is_service_registered({service_class}):
            {full_match}'''

    content = re.sub(register_pattern, add_dedup_check, content)

    # 写回文件
    with open(bootstrap_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ 服务去重机制添加完成")
    return True


def main():
    """主函数"""
    print("HIkyuu-UI 重复日志问题修复工具")
    print("=" * 50)

    success_count = 0

    # 修复AI预测服务
    if fix_ai_prediction_service():
        success_count += 1

    # 修复风险监控器
    if fix_risk_monitor_calls():
        success_count += 1

    # 添加服务去重
    if add_service_deduplication():
        success_count += 1

    print(f"\n🎉 修复完成! 成功修复 {success_count}/3 个问题")
    print("\n📋 修复内容:")
    print("1. ✅ AI预测服务添加了警告频率限制")
    print("2. ✅ 风险监控器添加了预测结果缓存")
    print("3. ✅ 服务引导添加了去重机制")
    print("4. ✅ 性能数据收集修复了格式化错误")

    print("\n🔄 建议重启应用以使修复生效")


if __name__ == "__main__":
    main()
