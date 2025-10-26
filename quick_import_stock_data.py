"""快速导入股票数据到DuckDB

此脚本用于首次使用时快速初始化股票数据。

功能:
1. 导入沪深A股股票列表
2. （可选）导入指定股票的K线数据

使用方法:
    python quick_import_stock_data.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


async def quick_import():
    """快速导入股票数据"""
    try:
        print("=" * 80)
        print("快速导入股票数据到DuckDB")
        print("=" * 80)

        # 导入必要的模块
        print("\n📦 加载模块...")
        from core.services.enhanced_duckdb_data_downloader import EnhancedDuckDBDataDownloader
        from datetime import datetime, timedelta

        # 创建下载器
        print("✓ 创建数据下载器")
        downloader = EnhancedDuckDBDataDownloader()

        # 1. 导入股票列表
        print("\n📥 步骤1: 导入股票列表")
        print("   正在从数据源获取沪深A股列表...")
        try:
            await downloader.download_stock_list(market='all')
            print("   ✅ 股票列表导入成功")
        except Exception as e:
            print(f"   ❌ 股票列表导入失败: {e}")
            print("   提示: 请检查网络连接和数据源配置")
            return False

        # 2. 询问是否导入K线数据
        print("\n📊 步骤2: K线数据导入（可选）")
        print("   K线数据量较大，建议先跳过，后续通过UI按需导入")
        print("   是否现在导入示例股票的K线数据？(y/N)")

        # 自动跳过K线导入（避免阻塞）
        import_kline = False
        print("   > 自动跳过K线导入")

        if import_kline:
            print("\n   正在导入示例股票K线数据...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # 最近30天

            # 示例股票
            sample_stocks = ['000001.SZ', '600000.SH', '000002.SZ']

            try:
                await downloader.download_kline_data(
                    symbols=sample_stocks,
                    start_date=start_date,
                    end_date=end_date
                )
                print("   ✅ 示例K线数据导入成功")
            except Exception as e:
                print(f"   ⚠️ K线数据导入失败: {e}")
                print("   提示: 可以稍后通过UI导入")

        print("\n" + "=" * 80)
        print("✅ 数据导入完成")
        print("=" * 80)
        print("\n下一步:")
        print("  1. 重启应用程序: python main.py")
        print("  2. 左侧面板应该显示股票列表")
        print("  3. 通过'数据管理 → K线专业数据导入'导入更多数据")
        print()

        return True

    except ImportError as e:
        print(f"\n❌ 模块导入失败: {e}")
        print("提示: 请确保在项目根目录下运行此脚本")
        return False
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        # 运行异步导入
        success = asyncio.run(quick_import())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断导入")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
