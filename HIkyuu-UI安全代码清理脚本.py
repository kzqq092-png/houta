#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HIkyuu-UI安全代码清理脚本

在统一架构改造完成后，安全清理不再需要的遗留代码和临时文件。
包含备份机制、依赖检查和回滚功能。

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-17
"""

import sys
import os
import shutil
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class SafeCodeCleaner:
    """安全代码清理器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "cleanup_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cleanup_log = []
        self.dependency_map = {}
        
        # 清理配置
        self.cleanup_config = {
            "safe_to_delete": {
                "description": "可以安全删除的文件",
                "files": [
                    "comprehensive_architecture_test.py",
                    "comprehensive_ui_system_test.py",
                    "adjusted_architecture_test.py", 
                    "validate_ui_components.py",
                    "verify_data_router.py",
                    "verify_data_standardization_engine.py",
                    "simple_ui_test.py",
                    "simple_test.py",
                    "simple_verification.py",
                    "verify_asset_aware_data_manager.py",
                    "verify_week1_implementation.py",
                    "tools/test_table_creation.py",
                    "tools/complete_table_schema_verification.py"
                ]
            },
            "mark_deprecated": {
                "description": "需要标记为废弃的文件",
                "files": [
                    "core/data_source.py",
                    "core/eastmoney_source.py", 
                    "core/sina_source.py",
                    "core/tonghuashun_source.py",
                    "core/akshare_data_source.py"
                ]
            },
            "backup_only": {
                "description": "仅备份但保留的重要文件",
                "files": [
                    "core/services/legacy_datasource_adapter.py",
                    "core/services/unified_data_manager.py"
                ]
            },
            "cleanup_directories": {
                "description": "需要清理的目录",
                "dirs": [
                    "backup",
                    "backups", 
                    "__pycache__",
                    "*.pyc"
                ]
            }
        }
    
    def create_backup(self) -> bool:
        """创建清理前的完整备份"""
        logger.info("🔄 创建清理前的完整备份...")
        
        try:
            # 创建备份目录
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 备份所有将要处理的文件
            all_files = (
                self.cleanup_config["safe_to_delete"]["files"] + 
                self.cleanup_config["mark_deprecated"]["files"] +
                self.cleanup_config["backup_only"]["files"]
            )
            
            backed_up_count = 0
            for file_path in all_files:
                source_file = self.project_root / file_path
                if source_file.exists():
                    # 创建备份文件的目录结构
                    backup_file = self.backup_dir / file_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(source_file, backup_file)
                    backed_up_count += 1
                    logger.debug(f"备份文件: {file_path}")
            
            # 创建备份清单
            backup_manifest = {
                "backup_time": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "backup_dir": str(self.backup_dir),
                "files_backed_up": backed_up_count,
                "cleanup_config": self.cleanup_config
            }
            
            with open(self.backup_dir / "backup_manifest.json", "w", encoding="utf-8") as f:
                json.dump(backup_manifest, f, indent=2, ensure_ascii=False)
            
            logger.success(f"✅ 备份完成，共备份 {backed_up_count} 个文件到: {self.backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return False
    
    def analyze_dependencies(self) -> Dict[str, Set[str]]:
        """分析文件依赖关系"""
        logger.info("🔍 分析文件依赖关系...")
        
        dependency_map = {}
        
        # 扫描所有Python文件
        for py_file in self.project_root.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 查找导入语句
                    imports = set()
                    for line in content.split("\n"):
                        line = line.strip()
                        if line.startswith("from ") or line.startswith("import "):
                            imports.add(line)
                    
                    relative_path = str(py_file.relative_to(self.project_root))
                    dependency_map[relative_path] = imports
                    
                except Exception as e:
                    logger.debug(f"分析文件依赖失败: {py_file}, {e}")
        
        self.dependency_map = dependency_map
        logger.success(f"✅ 依赖分析完成，分析了 {len(dependency_map)} 个文件")
        return dependency_map
    
    def check_file_usage(self, file_path: str) -> List[str]:
        """检查文件是否被其他文件使用"""
        file_stem = Path(file_path).stem
        usage_files = []
        
        for file, imports in self.dependency_map.items():
            for import_line in imports:
                if file_stem in import_line or file_path.replace("/", ".") in import_line:
                    usage_files.append(file)
        
        return usage_files
    
    def safe_delete_files(self) -> bool:
        """安全删除文件"""
        logger.info("🗑️  开始安全删除文件...")
        
        deleted_count = 0
        skipped_count = 0
        
        for file_path in self.cleanup_config["safe_to_delete"]["files"]:
            source_file = self.project_root / file_path
            
            if not source_file.exists():
                logger.debug(f"文件不存在，跳过: {file_path}")
                continue
            
            # 检查文件使用情况
            usage_files = self.check_file_usage(file_path)
            if usage_files:
                logger.warning(f"⚠️  文件 {file_path} 被以下文件使用，跳过删除:")
                for usage_file in usage_files[:3]:  # 只显示前3个
                    logger.warning(f"    - {usage_file}")
                if len(usage_files) > 3:
                    logger.warning(f"    - ... 还有 {len(usage_files) - 3} 个文件")
                skipped_count += 1
                continue
            
            try:
                # 删除文件
                source_file.unlink()
                deleted_count += 1
                logger.info(f"✅ 已删除: {file_path}")
                
                self.cleanup_log.append({
                    "action": "deleted",
                    "file": file_path,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ 删除失败: {file_path}, {e}")
                skipped_count += 1
        
        logger.success(f"✅ 文件删除完成，删除 {deleted_count} 个，跳过 {skipped_count} 个")
        return True
    
    def mark_deprecated_files(self) -> bool:
        """标记文件为废弃"""
        logger.info("🏷️  标记废弃文件...")
        
        deprecated_header = '''"""
⚠️  DEPRECATED: This file is deprecated and will be removed in future versions.
⚠️  废弃警告: 此文件已废弃，将在未来版本中移除。

Please use the new plugin-based architecture instead:
请使用新的基于插件的架构:
- UniPluginDataManager for unified data access
- IDataSourcePlugin for data source implementations  
- Standard plugin templates in plugins/templates/

Migration date: {migration_date}
Reason: Replaced by unified plugin architecture
"""

'''
        
        marked_count = 0
        
        for file_path in self.cleanup_config["mark_deprecated"]["files"]:
            source_file = self.project_root / file_path
            
            if not source_file.exists():
                logger.debug(f"文件不存在，跳过: {file_path}")
                continue
            
            try:
                # 读取原文件内容
                with open(source_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 检查是否已经标记
                if "DEPRECATED" in content:
                    logger.debug(f"文件已标记为废弃，跳过: {file_path}")
                    continue
                
                # 添加废弃标记
                deprecated_notice = deprecated_header.format(
                    migration_date=datetime.now().strftime("%Y-%m-%d")
                )
                
                # 在文件开头添加废弃标记
                new_content = deprecated_notice + content
                
                # 写回文件
                with open(source_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                marked_count += 1
                logger.info(f"✅ 已标记为废弃: {file_path}")
                
                self.cleanup_log.append({
                    "action": "marked_deprecated",
                    "file": file_path,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ 标记废弃失败: {file_path}, {e}")
        
        logger.success(f"✅ 废弃标记完成，标记了 {marked_count} 个文件")
        return True
    
    def cleanup_cache_files(self) -> bool:
        """清理缓存文件"""
        logger.info("🧹 清理缓存文件...")
        
        cleaned_count = 0
        
        # 清理__pycache__目录
        for pycache_dir in self.project_root.rglob("__pycache__"):
            if pycache_dir.is_dir():
                try:
                    shutil.rmtree(pycache_dir)
                    cleaned_count += 1
                    logger.debug(f"删除缓存目录: {pycache_dir.relative_to(self.project_root)}")
                except Exception as e:
                    logger.warning(f"删除缓存目录失败: {pycache_dir}, {e}")
        
        # 清理.pyc文件
        for pyc_file in self.project_root.rglob("*.pyc"):
            try:
                pyc_file.unlink()
                cleaned_count += 1
                logger.debug(f"删除缓存文件: {pyc_file.relative_to(self.project_root)}")
            except Exception as e:
                logger.warning(f"删除缓存文件失败: {pyc_file}, {e}")
        
        logger.success(f"✅ 缓存清理完成，清理了 {cleaned_count} 个项目")
        return True
    
    def generate_cleanup_report(self) -> str:
        """生成清理报告"""
        report = []
        report.append("=" * 80)
        report.append("HIkyuu-UI代码清理报告")
        report.append("=" * 80)
        report.append(f"清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"项目路径: {self.project_root}")
        report.append(f"备份路径: {self.backup_dir}")
        report.append("")
        
        # 统计清理结果
        deleted_files = [log for log in self.cleanup_log if log["action"] == "deleted"]
        deprecated_files = [log for log in self.cleanup_log if log["action"] == "marked_deprecated"]
        
        report.append("📊 清理统计:")
        report.append(f"  • 删除文件数: {len(deleted_files)}")
        report.append(f"  • 标记废弃数: {len(deprecated_files)}")
        report.append(f"  • 分析文件数: {len(self.dependency_map)}")
        report.append("")
        
        # 详细清理日志
        if deleted_files:
            report.append("🗑️  已删除文件:")
            for log in deleted_files:
                report.append(f"  ✅ {log['file']}")
            report.append("")
        
        if deprecated_files:
            report.append("🏷️  已标记废弃:")
            for log in deprecated_files:
                report.append(f"  ⚠️  {log['file']}")
            report.append("")
        
        # 回滚说明
        report.append("🔄 回滚说明:")
        report.append(f"  如需回滚，请执行以下命令:")
        report.append(f"  python HIkyuu-UI安全代码清理脚本.py --rollback {self.backup_dir}")
        report.append("")
        
        # 建议
        report.append("💡 后续建议:")
        report.append("  1. 运行完整测试套件验证系统功能")
        report.append("  2. 检查是否有新的编译或导入错误")
        report.append("  3. 更新相关文档和说明")
        report.append("  4. 如发现问题，可使用备份进行回滚")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def rollback(self, backup_path: str) -> bool:
        """从备份回滚"""
        logger.info(f"🔄 开始从备份回滚: {backup_path}")
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            logger.error(f"❌ 备份目录不存在: {backup_path}")
            return False
        
        # 读取备份清单
        manifest_file = backup_dir / "backup_manifest.json"
        if not manifest_file.exists():
            logger.error("❌ 备份清单文件不存在")
            return False
        
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            restored_count = 0
            
            # 恢复所有备份文件
            for backup_file in backup_dir.rglob("*"):
                if backup_file.is_file() and backup_file.name != "backup_manifest.json":
                    relative_path = backup_file.relative_to(backup_dir)
                    target_file = self.project_root / relative_path
                    
                    # 创建目标目录
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 恢复文件
                    shutil.copy2(backup_file, target_file)
                    restored_count += 1
                    logger.debug(f"恢复文件: {relative_path}")
            
            logger.success(f"✅ 回滚完成，恢复了 {restored_count} 个文件")
            return True
            
        except Exception as e:
            logger.error(f"❌ 回滚失败: {e}")
            return False
    
    def run_cleanup(self, dry_run: bool = False) -> bool:
        """运行完整清理流程"""
        logger.info("🚀 开始HIkyuu-UI代码清理...")
        
        if dry_run:
            logger.info("🔍 运行模式: 预览模式 (不会实际修改文件)")
        
        try:
            # 1. 分析依赖关系
            self.analyze_dependencies()
            
            # 2. 创建备份
            if not dry_run and not self.create_backup():
                return False
            
            # 3. 安全删除文件
            if not dry_run:
                self.safe_delete_files()
            else:
                logger.info("🔍 预览: 将删除以下文件:")
                for file_path in self.cleanup_config["safe_to_delete"]["files"]:
                    if (self.project_root / file_path).exists():
                        usage_files = self.check_file_usage(file_path)
                        if usage_files:
                            logger.info(f"  ⚠️  {file_path} (被 {len(usage_files)} 个文件使用)")
                        else:
                            logger.info(f"  ✅ {file_path}")
            
            # 4. 标记废弃文件
            if not dry_run:
                self.mark_deprecated_files()
            else:
                logger.info("🔍 预览: 将标记以下文件为废弃:")
                for file_path in self.cleanup_config["mark_deprecated"]["files"]:
                    if (self.project_root / file_path).exists():
                        logger.info(f"  🏷️  {file_path}")
            
            # 5. 清理缓存文件
            if not dry_run:
                self.cleanup_cache_files()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 清理失败: {e}")
            logger.error(traceback.format_exc())
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HIkyuu-UI安全代码清理脚本")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际修改文件")
    parser.add_argument("--rollback", type=str, help="从指定备份路径回滚")
    parser.add_argument("--project-root", type=str, default=".", help="项目根目录")
    
    args = parser.parse_args()
    
    project_root = os.path.abspath(args.project_root)
    logger.info(f"🚀 启动HIkyuu-UI安全代码清理脚本...")
    logger.info(f"📁 项目路径: {project_root}")
    
    cleaner = SafeCodeCleaner(project_root)
    
    try:
        if args.rollback:
            # 回滚模式
            success = cleaner.rollback(args.rollback)
            if success:
                logger.success("🎉 回滚成功！")
                return 0
            else:
                logger.error("❌ 回滚失败！")
                return 1
        else:
            # 清理模式
            success = cleaner.run_cleanup(dry_run=args.dry_run)
            
            if success and not args.dry_run:
                # 生成并保存报告
                report = cleaner.generate_cleanup_report()
                logger.info("\n" + report)
                
                report_file = f"HIkyuu-UI代码清理报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                logger.info(f"📄 清理报告已保存到: {report_file}")
                logger.success("🎉 代码清理完成！")
                return 0
            elif success and args.dry_run:
                logger.success("🎉 预览完成！使用 --dry-run=false 执行实际清理")
                return 0
            else:
                logger.error("❌ 清理失败！")
                return 1
    
    except Exception as e:
        logger.error(f"❌ 脚本执行失败: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
