#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描所有插件的name字段状态
检查哪些插件缺少或name不友好
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class PluginNameScanner:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.results = []

    def scan_all_plugins(self) -> List[Dict[str, Any]]:
        """扫描所有插件文件"""
        plugin_files = []

        # 递归查找所有.py文件
        for py_file in self.plugins_dir.rglob("*.py"):
            # 跳过__init__.py和测试文件
            if py_file.name in ["__init__.py"] or py_file.name.startswith("test_"):
                continue

            # 跳过examples-del目录（已标记删除）
            if "examples-del" in str(py_file):
                continue

            plugin_files.append(py_file)

        print(f"找到 {len(plugin_files)} 个插件文件\n")

        for plugin_file in sorted(plugin_files):
            result = self.scan_plugin_file(plugin_file)
            if result:
                self.results.append(result)

        return self.results

    def scan_plugin_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """扫描单个插件文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            result = {
                'file': str(file_path.relative_to(self.plugins_dir.parent)),
                'class_name': None,
                'has_plugin_info': False,
                'name_field': None,
                'display_name_field': None,
                'description': None,
                'author': None,
                'version': None,
                'status': 'unknown',
                'issues': []
            }

            # 查找类定义
            class_match = re.search(r'class\s+(\w+)\s*\(.*Plugin.*\):', content)
            if class_match:
                result['class_name'] = class_match.group(1)

            # 查找PluginInfo定义
            # 模式1: 返回PluginInfo(...)
            plugin_info_pattern = r'PluginInfo\s*\((.*?)\)'
            plugin_info_matches = re.findall(plugin_info_pattern, content, re.DOTALL)

            if plugin_info_matches:
                result['has_plugin_info'] = True
                # 取第一个匹配（通常是主要的PluginInfo）
                plugin_info_content = plugin_info_matches[0]

                # 提取字段值
                result['name_field'] = self._extract_field(plugin_info_content, 'name')
                result['display_name_field'] = self._extract_field(plugin_info_content, 'display_name')
                result['description'] = self._extract_field(plugin_info_content, 'description')
                result['author'] = self._extract_field(plugin_info_content, 'author')
                result['version'] = self._extract_field(plugin_info_content, 'version')

            # 模式2: self.plugin_info = PluginInfo(...)
            elif 'self.plugin_info' in content or 'self._plugin_info' in content:
                result['has_plugin_info'] = True
                # 尝试提取内联定义
                inline_pattern = r'self\._?plugin_info\s*=\s*PluginInfo\s*\((.*?)\)'
                inline_match = re.search(inline_pattern, content, re.DOTALL)
                if inline_match:
                    plugin_info_content = inline_match.group(1)
                    result['name_field'] = self._extract_field(plugin_info_content, 'name')
                    result['display_name_field'] = self._extract_field(plugin_info_content, 'display_name')

            # 模式3: 直接定义属性
            elif 'self.name' in content:
                name_match = re.search(r'self\.name\s*=\s*["\']([^"\']+)["\']', content)
                if name_match:
                    result['name_field'] = name_match.group(1)

            # 判断状态
            result['status'] = self._evaluate_status(result)

            return result

        except Exception as e:
            print(f"❌ 扫描失败 {file_path}: {e}")
            return None

    def _extract_field(self, content: str, field_name: str) -> Optional[str]:
        """从PluginInfo内容中提取字段值"""
        # 匹配 field_name="value" 或 field_name='value'
        pattern = rf'{field_name}\s*=\s*["\']([^"\']+)["\']'
        match = re.search(pattern, content)
        if match:
            return match.group(1)

        # 匹配 field_name=f"value" 或 field_name=f'value'
        pattern_f = rf'{field_name}\s*=\s*f["\']([^"\']+)["\']'
        match_f = re.search(pattern_f, content)
        if match_f:
            return match_f.group(1)

        return None

    def _evaluate_status(self, result: Dict[str, Any]) -> str:
        """评估插件状态"""
        issues = []

        if not result['has_plugin_info']:
            issues.append("缺少PluginInfo定义")
            result['issues'] = issues
            return "❌ 无PluginInfo"

        if not result['name_field'] and not result['display_name_field']:
            issues.append("缺少name/display_name字段")
            result['issues'] = issues
            return "❌ 无name"

        name = result['name_field'] or result['display_name_field']

        # 检查name是否友好
        if not name:
            issues.append("name为空")
            return "❌ name为空"

        # 不友好的name特征
        if '_' in name and name.islower():
            issues.append(f"name不友好（{name}）- 包含下划线且全小写")
            result['issues'] = issues
            return "⚠️ name不友好"

        if name.endswith('_plugin') or name.endswith('Plugin'):
            issues.append(f"name包含Plugin后缀（{name}）")
            result['issues'] = issues
            return "⚠️ 需优化"

        if len(name) < 3:
            issues.append(f"name过短（{name}）")
            result['issues'] = issues
            return "⚠️ name过短"

        # 检查其他必填字段
        if not result['description']:
            issues.append("缺少description")

        if not result['version']:
            issues.append("缺少version")

        if issues:
            result['issues'] = issues
            return "⚠️ 部分缺失"

        result['issues'] = issues
        return "✅ 完整"

    def generate_report(self):
        """生成报告"""
        print("=" * 80)
        print("插件Name字段扫描报告")
        print("=" * 80)
        print()

        # 按状态分类
        by_status = {
            "✅ 完整": [],
            "⚠️ name不友好": [],
            "⚠️ 需优化": [],
            "⚠️ 部分缺失": [],
            "⚠️ name过短": [],
            "❌ 无name": [],
            "❌ 无PluginInfo": [],
            "❌ name为空": []
        }

        for result in self.results:
            status = result['status']
            by_status[status].append(result)

        # 统计
        total = len(self.results)
        complete = len(by_status["✅ 完整"])
        needs_fix = total - complete

        print(f"📊 总计: {total} 个插件")
        print(f"✅ 完整: {complete} 个 ({complete/total*100:.1f}%)")
        print(f"⚠️❌ 需修复: {needs_fix} 个 ({needs_fix/total*100:.1f}%)")
        print()

        # 详细报告
        for status, plugins in by_status.items():
            if plugins:
                print(f"\n{status} ({len(plugins)}个)")
                print("-" * 80)
                for p in plugins:
                    name = p['name_field'] or p['display_name_field'] or "无"
                    print(f"  📄 {p['file']}")
                    print(f"     类名: {p['class_name'] or '未知'}")
                    print(f"     name: {name}")
                    if p['description']:
                        print(f"     描述: {p['description'][:50]}...")
                    if p['issues']:
                        print(f"     问题: {', '.join(p['issues'])}")
                    print()

        # 保存JSON结果
        output_file = "plugin_name_scan_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'complete': complete,
                    'needs_fix': needs_fix
                },
                'by_status': {k: len(v) for k, v in by_status.items()},
                'details': self.results
            }, f, ensure_ascii=False, indent=2)

        print(f"\n💾 详细结果已保存到: {output_file}")

        return by_status


if __name__ == "__main__":
    scanner = PluginNameScanner()
    scanner.scan_all_plugins()
    by_status = scanner.generate_report()

    # 生成修复建议
    print("\n" + "=" * 80)
    print("🔧 修复建议")
    print("=" * 80)

    unfriendly = by_status.get("⚠️ name不友好", [])
    needs_optimize = by_status.get("⚠️ 需优化", [])
    no_name = by_status.get("❌ 无name", []) + by_status.get("❌ name为空", [])

    if unfriendly or needs_optimize:
        print("\n需要优化友好名称的插件:")
        for p in unfriendly + needs_optimize:
            current_name = p['name_field'] or p['display_name_field']
            file_base = Path(p['file']).stem

            # 建议友好名称
            suggested = file_base.replace('_plugin', '').replace('_', ' ').title()

            # 特殊处理
            mapping = {
                'akshare': 'AKShare',
                'eastmoney': '东方财富',
                'sina': '新浪财经',
                'tongdaxin': '通达信',
                'binance': 'Binance',
                'huobi': '火币',
                'okx': 'OKX',
                'coinbase': 'Coinbase',
                'yahoo finance': 'Yahoo Finance',
                'wenhua': '文华财经',
                'cninfo': '巨潮资讯',
                'talib': 'TA-Lib',
                'pandas ta': 'Pandas TA',
                'hikyuu': 'Hikyuu',
                'backtrader': 'Backtrader',
            }

            suggested_lower = suggested.lower()
            if suggested_lower in mapping:
                suggested = mapping[suggested_lower]

            print(f"  📄 {p['file']}")
            print(f"     当前: '{current_name}' → 建议: '{suggested}'")

    if no_name:
        print("\n需要添加name字段的插件:")
        for p in no_name:
            print(f"  📄 {p['file']}")
            print(f"     类名: {p['class_name']}")
