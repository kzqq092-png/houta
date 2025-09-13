"""简单验证脚本"""

print("开始验证第1周实现...")

# 测试1: 导入检查
try:
    from core.asset_type_identifier import get_asset_type_identifier
    from core.asset_database_manager import AssetSeparatedDatabaseManager, AssetDatabaseConfig
    from core.plugin_types import AssetType
    print("✅ 所有模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    exit(1)

# 测试2: 基本功能
try:
    identifier = get_asset_type_identifier()
    result = identifier.identify_asset_type_by_symbol("000001.SZ")
    print(f"✅ 资产识别功能正常: 000001.SZ -> {result.value}")
except Exception as e:
    print(f"❌ 资产识别失败: {e}")
    exit(1)

# 测试3: 数据库管理器创建
try:
    import tempfile
    temp_dir = tempfile.mkdtemp()
    config = AssetDatabaseConfig(base_path=temp_dir, pool_size=1)
    manager = AssetSeparatedDatabaseManager(config)
    print("✅ 数据库管理器创建成功")
except Exception as e:
    print(f"❌ 数据库管理器创建失败: {e}")
    exit(1)

print("\n🎉 基本验证通过！核心组件可以正常工作！")
print("✅ 第1周实现验证完成，可以进行下一步开发")

# 清理
try:
    manager.close_all_connections()
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("✅ 清理完成")
except:
    pass
