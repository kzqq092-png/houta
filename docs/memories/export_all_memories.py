#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出所有Serena记忆体数据到本地文件
确保后续可以导入使用
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def export_all_memories():
    """导出所有记忆体到本地文件"""
    
    # 创建导出目录
    export_dir = Path(__file__).parent / "exported_memories"
    export_dir.mkdir(exist_ok=True)
    
    # 记忆体列表（从list_memories获取）
    memories = [
        "AKShare_DataSource_Lookup_Fix",
        "AKShare_DataSource_Lookup_Fix_Complete",
        "AKShare_Empty_Data_Handling_Final_Solution",
        "Async_Batch_Dialog_And_AKShare_API_Fix",
        "Batch_Dialog_Async_Correct_Fix",
        "Batch_Dialog_Import_Fix_Final",
        "Batch_Selection_Async_Fix",
        "BATCH_SELECTION_OFFICIAL_API_MODIFICATION",
        "Complete_Fix_Summary_UI_Async_AKShare",
        "database_admin_dialog_duckdb_full_support",
        "database_architecture_and_asset_metadata_fix",
        "database_architecture_migration_analysis",
        "data_import_features_analysis",
        "Data_Quality_0_Root_Cause_And_Fix",
        "Data_Quality_Score_0_Root_Cause",
        "DATA_SOURCE_USAGE_CLARIFICATION",
        "db_models功能完整性检查_2025_10_23",
        "db_models目录分析_2025_10_23",
        "distributed_node_implementation",
        "distributed_system_final_summary",
        "distributed_task_allocation_and_data_flow",
        "distributed_ui_comparison",
        "Final_Data_Quality_Fix_Summary",
        "KLINE_IMPORT_FIX_COMPLETED",
        "KLine_Parameter_Conversion_Fix",
        "K_Line_Import_Asset_Metadata_Root_Cause_Analysis",
        "None_Value_Attribute_Error_Fix",
        "project_overview",
        "STOCK_DATA_SOURCE_CONSISTENCY_ANALYSIS",
        "suggested_commands",
        "Task_List_Persistence_Fix",
        "Task_Status_Display_Fix",
        "TONGDAXIN_A_STOCK_FILTER_FIX",
        "TONGDAXIN_DATA_DIFFERENCE_FIX",
        "TONGDAXIN_MULTIPROCESS_COMPLETION",
        "TONGDAXIN_MULTIPROCESS_MODIFICATION",
        "TONGDAXIN_PLUGIN_FIX_SUCCESS_VERIFICATION",
        "TONGDAXIN_PLUGIN_LARGE_DATA_FIX",
        "unified_best_quality_kline_view_logic",
        "ValidationResult_参数修复_2025_10_23",
        "历史K线表字段名修复_2025_10_23",
        "数据库目录统一和修复指南_2025_10_23",
        "数据库目录统一完成_2025_10_23",
        "数据库路径全面审查完成_2025_10_23",
        "新架构表结构修复_2025_10_23"
    ]
    
    print(f"开始导出 {len(memories)} 个记忆体...")
    print(f"导出目录: {export_dir.absolute()}")
    print("=" * 80)
    
    exported_count = 0
    skipped_count = 0
    
    for memory_name in memories:
        try:
            # 生成安全的文件名
            safe_name = memory_name.replace("/", "_").replace("\\", "_").replace(":", "_")
            output_file = export_dir / f"{safe_name}.md"
            
            # 这里需要手动复制记忆体内容
            # 由于无法直接调用read_memory工具，需要手动导出
            print(f"[MANUAL] 请手动导出: {memory_name}")
            print(f"         目标文件: {output_file}")
            print()
            
            skipped_count += 1
            
        except Exception as e:
            print(f"[ERROR] 导出失败 {memory_name}: {e}")
    
    print("=" * 80)
    print(f"导出完成！需要手动导出 {skipped_count} 个记忆体")
    print(f"导出目录: {export_dir.absolute()}")
    
if __name__ == "__main__":
    export_all_memories()

