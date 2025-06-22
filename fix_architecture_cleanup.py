#!/usr/bin/env python3
"""
HIkyuu指标架构清理脚本
修复参数名不统一和重复导入问题
"""

import os
import re
import sys
from pathlib import Path


class ArchitectureCleanup:
    """指标架构清理器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = 0
        self.files_processed = 0

        # 参数名映射规则
        self.param_mappings = {
            # 标准化参数名映射
            r'period': 'period',
            r'fast_period': 'fast_period',
            r'slow_period': 'slow_period',
            r'signal_period': 'signal_period',
            r'std_dev': 'std_dev',
            r'std_dev': 'std_dev',
            r'k_period': 'k_period',
            r'd_period': 'd_period',
            r'j_period': 'j_period',
        }

        # 需要保留兼容性的文件（直接调用TA-Lib的地方）
        self.talib_compatible_files = {
            'core/services/engines/talib_engine.py',
            'core/services/engines/fallback_engine.py',
            'test_unified_indicators.py',  # TA-Lib测试部分保持原样
        }

    def run_cleanup(self):
        """运行完整的清理过程"""
        print("开始HIkyuu指标架构清理...")
        print("=" * 50)

        # 步骤1：修复参数名不统一问题
        self.fix_parameter_names()

        # 步骤2：清理重复导入
        self.cleanup_duplicate_imports()

        # 步骤3：更新import语句使用新架构
        self.update_import_statements()

        # 步骤4：验证修复结果
        self.verify_fixes()

        print("\n" + "=" * 50)
        print(f"清理完成！共处理 {self.files_processed} 个文件，应用 {self.fixes_applied} 个修复")

    def fix_parameter_names(self):
        """修复参数名不统一问题"""
        print("\n📝 步骤1：修复参数名不统一问题")

        # 查找所有Python文件
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            # 跳过TA-Lib兼容文件
            if any(compat in str(file_path) for compat in self.talib_compatible_files):
                continue

            try:
                self._fix_file_parameters(file_path)
            except Exception as e:
                print(f"⚠️  处理文件 {file_path} 时出错: {e}")

    def _fix_file_parameters(self, file_path: Path):
        """修复单个文件的参数名"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original_content = content

        # 修复字典形式的参数
        for old_param, new_param in self.param_mappings.items():
            # 匹配字典中的参数：{'period': 20} -> {'period': 20}
            pattern = rf"['\"]({old_param})['\"]\s*:"
            replacement = rf"'{new_param}':"
            content = re.sub(pattern, replacement, content)

            # 匹配函数参数中的参数：period=20 -> period=20 (但保留talib调用)
            if 'talib.' not in content or not re.search(r'talib\.\w+.*' + old_param, content):
                pattern = rf"\b{old_param}\s*="
                replacement = f"{new_param}="
                content = re.sub(pattern, replacement, content)

        # 如果文件有修改，保存并记录
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复参数名: {file_path}")
            self.fixes_applied += 1

        self.files_processed += 1

    def cleanup_duplicate_imports(self):
        """清理重复导入"""
        print("\n🧹 步骤2：清理重复导入")

        # 找到有重复导入的文件
        duplicate_import_files = [
            'gui/widgets/chart_widget.py',
            'gui/widgets/analysis_widget.py',
            'gui/widgets/async_data_processor.py',
            'gui/panels/stock_panel.py',
            'core/stock_screener.py',
            'core/system_condition.py',
            'analysis/technical_analysis.py',
            'features/basic_indicators.py',
            'components/stock_screener.py',
        ]

        for file_rel_path in duplicate_import_files:
            file_path = self.project_root / file_rel_path
            if file_path.exists():
                self._cleanup_file_imports(file_path)

    def _cleanup_file_imports(self, file_path: Path):
        """清理单个文件的重复导入"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        cleaned_lines = []
        imports_seen = set()

        for line in lines:
            # 检查是否为导入语句
            if line.strip().startswith('from core.indicator_manager import') and \
               '# 兼容层' in line:
                # 保留注释，但标记为已处理
                if 'core.indicator_manager' not in imports_seen:
                    cleaned_lines.append(line)
                    imports_seen.add('core.indicator_manager')

            elif line.strip().startswith('from core.unified_indicator_manager import'):
                # 统一指标管理器导入
                if 'core.unified_indicator_manager' not in imports_seen:
                    cleaned_lines.append(line)
                    imports_seen.add('core.unified_indicator_manager')

            else:
                cleaned_lines.append(line)

        # 保存清理后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)

        print(f"✓ 清理重复导入: {file_path}")
        self.fixes_applied += 1

    def update_import_statements(self):
        """更新导入语句使用新架构"""
        print("\n🔄 步骤3：更新导入语句使用新架构")

        # 需要更新的主要UI文件
        ui_files = [
            'gui/widgets/chart_widget.py',
            'gui/widgets/analysis_widget.py',
            'gui/panels/stock_panel.py',
        ]

        for file_rel_path in ui_files:
            file_path = self.project_root / file_rel_path
            if file_path.exists():
                self._update_file_imports(file_path)

    def _update_file_imports(self, file_path: Path):
        """更新单个文件的导入语句"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 在现有导入后添加新架构导入（如果还没有）
        if 'from core.services import get_indicator_ui_adapter' not in content:
            # 找到core导入的位置
            import_section = re.search(r'(from core\..*?import.*?\n)', content)
            if import_section:
                new_import = '''
# 更新：优先使用新的指标服务架构
try:
    from core.services import get_indicator_ui_adapter
    _use_new_architecture = True
except ImportError:
    get_indicator_ui_adapter = None
    _use_new_architecture = False
'''
                content = content.replace(import_section.group(1),
                                          import_section.group(1) + new_import)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"✓ 更新导入语句: {file_path}")
                self.fixes_applied += 1

    def verify_fixes(self):
        """验证修复结果"""
        print("\n✅ 步骤4：验证修复结果")

        issues_found = []

        # 检查是否还有旧参数名
        python_files = list(self.project_root.rglob("*.py"))
        for file_path in python_files:
            if any(compat in str(file_path) for compat in self.talib_compatible_files):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查是否还有旧参数名（排除talib调用）
                for old_param in self.param_mappings.keys():
                    if old_param in content and 'talib.' not in content:
                        # 进一步检查，确保不是在talib调用中
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if old_param in line and 'talib.' not in line:
                                issues_found.append(f"{file_path}:{i+1} - 仍有旧参数名: {old_param}")

            except Exception as e:
                print(f"⚠️  验证文件 {file_path} 时出错: {e}")

        if issues_found:
            print("❌ 发现需要手动修复的问题:")
            for issue in issues_found[:10]:  # 只显示前10个
                print(f"  {issue}")
            if len(issues_found) > 10:
                print(f"  ... 还有 {len(issues_found) - 10} 个问题")
        else:
            print("✅ 所有参数名已成功标准化")


def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))

    print("HIkyuu指标架构自动清理工具")
    print("=" * 50)
    print(f"项目根目录: {project_root}")

    # 创建清理器并运行
    cleanup = ArchitectureCleanup(project_root)
    cleanup.run_cleanup()

    print("\n🎉 架构清理完成！")
    print("\n建议接下来的步骤:")
    print("1. 运行测试验证功能正常: python test_quick_validation.py")
    print("2. 检查UI组件是否正常工作")
    print("3. 验证新指标架构的性能表现")


if __name__ == "__main__":
    main()
