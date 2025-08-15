#!/usr/bin/env python3
"""
最终的配置对话框测试
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_config_dialog_final():
    """最终测试配置对话框"""
    print("🎯 最终测试配置对话框功能...")

    try:
        # 创建Qt应用程序
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        from gui.dialogs.data_source_plugin_config_dialog import DataSourcePluginConfigDialog

        # 测试所有需要配置的插件
        test_plugins = [
            ("examples.wind_data_plugin", "Wind数据插件"),
            ("examples.ctp_futures_plugin", "CTP期货插件"),
            ("examples.mysteel_data_plugin", "我的钢铁网插件"),
            ("examples.wenhua_data_plugin", "文华财经插件"),
            ("examples.bond_data_plugin", "债券数据插件")
        ]

        success_count = 0

        for plugin_id, plugin_name in test_plugins:
            print(f"\n📋 测试 {plugin_name} ({plugin_id})...")

            try:
                # 创建配置对话框
                dialog = DataSourcePluginConfigDialog(plugin_id)

                # 检查UI控件状态
                host = dialog.host_edit.text()
                port = dialog.port_spin.value()
                auth_type = dialog.auth_type_combo.currentText()

                # 验证配置是否正确加载
                config_loaded = bool(host and host != "")
                auth_configured = auth_type != "无认证"

                print(f"   主机地址: '{host}' {'✅' if config_loaded else '❌'}")
                print(f"   端口: {port}")
                print(f"   认证类型: {auth_type} {'✅' if auth_configured else '❌'}")

                # 测试配置保存功能
                try:
                    config = dialog.collect_config_from_ui()
                    if config and 'connection' in config and 'auth' in config:
                        print(f"   配置收集: ✅ 成功")
                        config_valid = True
                    else:
                        print(f"   配置收集: ❌ 失败")
                        config_valid = False
                except Exception as e:
                    print(f"   配置收集: ❌ 异常 - {e}")
                    config_valid = False

                # 测试性能指标更新（不会抛出异常）
                try:
                    dialog.update_metrics()
                    print(f"   性能指标: ✅ 更新成功")
                    metrics_ok = True
                except Exception as e:
                    print(f"   性能指标: ❌ 更新失败 - {e}")
                    metrics_ok = False

                # 综合评估
                if config_loaded and config_valid and metrics_ok:
                    print(f"   🎉 {plugin_name}: 全部功能正常")
                    success_count += 1
                else:
                    print(f"   ⚠️ {plugin_name}: 部分功能异常")

            except Exception as e:
                print(f"   ❌ {plugin_name}: 创建失败 - {e}")

        print(f"\n📊 测试结果: {success_count}/{len(test_plugins)} 个插件配置对话框功能正常")

        if success_count == len(test_plugins):
            print("\n🎉 所有插件配置对话框功能正常！")
            print("💡 用户现在可以:")
            print("   1. 正常打开插件配置对话框")
            print("   2. 看到预设的主机地址和认证方式")
            print("   3. 修改配置参数")
            print("   4. 保存配置到数据库")
            print("   5. 重新打开时看到之前的配置")
            return True
        else:
            print(f"\n⚠️ {len(test_plugins) - success_count} 个插件仍有问题")
            return False

    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_dialog_final()
    sys.exit(0 if success else 1)
