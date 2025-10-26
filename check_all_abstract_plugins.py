"""检查所有插件，找出哪些被标记为抽象类"""
import sys
import inspect
from pathlib import Path
from abc import ABCMeta

sys.path.insert(0, str(Path(__file__).parent))


def check_plugin_file(file_path: Path):
    """检查单个插件文件"""
    try:
        # 构建模块路径
        relative_path = file_path.relative_to(Path.cwd())
        module_path = str(relative_path.with_suffix('')).replace('\\', '.').replace('/', '.')

        # 跳过__init__文件和非Python文件
        if file_path.name == '__init__.py' or file_path.suffix != '.py':
            return None

        # 跳过测试文件
        if 'test_' in file_path.name or '_test' in file_path.name:
            return None

        # 导入模块
        try:
            module = __import__(module_path, fromlist=['*'])
        except Exception as e:
            return {
                'file': str(file_path),
                'module': module_path,
                'status': 'import_error',
                'error': str(e)
            }

        # 查找插件类
        plugin_classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # 检查是否是插件类（名称包含Plugin或继承自插件基类）
            if 'Plugin' in name or 'plugin' in name.lower():
                # 检查是否定义在当前模块中
                if obj.__module__ == module_path:
                    plugin_classes.append((name, obj))

        if not plugin_classes:
            return None

        # 检查每个插件类
        results = []
        for class_name, plugin_class in plugin_classes:
            # 检查是否是抽象类
            is_abstract = inspect.isabstract(plugin_class)
            is_abc = isinstance(plugin_class, ABCMeta)

            # 获取抽象方法
            abstract_methods = []
            if hasattr(plugin_class, '__abstractmethods__'):
                abstract_methods = list(plugin_class.__abstractmethods__)

            # 尝试实例化
            can_instantiate = False
            instantiate_error = None
            if not is_abstract:
                try:
                    instance = plugin_class()
                    can_instantiate = True
                except TypeError as e:
                    if 'abstract' in str(e).lower():
                        is_abstract = True
                        instantiate_error = str(e)
                except Exception as e:
                    instantiate_error = f"{type(e).__name__}: {e}"

            results.append({
                'file': str(file_path),
                'module': module_path,
                'class': class_name,
                'is_abstract': is_abstract,
                'is_abc': is_abc,
                'abstract_methods': abstract_methods,
                'can_instantiate': can_instantiate,
                'instantiate_error': instantiate_error,
                'status': 'abstract' if is_abstract else 'concrete'
            })

        return results

    except Exception as e:
        return {
            'file': str(file_path),
            'status': 'check_error',
            'error': str(e)
        }


def main():
    """主函数"""
    print("="*80)
    print("检查所有插件，识别抽象类")
    print("="*80)
    print()

    # 查找所有插件目录
    plugin_dirs = [
        Path('plugins/data_sources'),
        Path('plugins/indicators'),
        Path('plugins/strategies'),
        Path('plugins/sentiment_data_sources'),
    ]

    all_results = []

    for plugin_dir in plugin_dirs:
        if not plugin_dir.exists():
            print(f"[SKIP] 目录不存在: {plugin_dir}")
            continue

        print(f"\n[检查] {plugin_dir}")
        print("-"*80)

        # 递归查找所有Python文件
        for py_file in plugin_dir.rglob('*.py'):
            result = check_plugin_file(py_file)
            if result:
                if isinstance(result, list):
                    all_results.extend(result)
                else:
                    all_results.append(result)

    # 分类统计
    print("\n" + "="*80)
    print("检查结果汇总")
    print("="*80)

    abstract_plugins = [r for r in all_results if isinstance(r, dict) and r.get('status') == 'abstract']
    concrete_plugins = [r for r in all_results if isinstance(r, dict) and r.get('status') == 'concrete']
    error_plugins = [r for r in all_results if isinstance(r, dict) and r.get('status') in ['import_error', 'check_error']]

    print(f"\n[统计]")
    print(f"  抽象类插件: {len(abstract_plugins)}")
    print(f"  具体类插件: {len(concrete_plugins)}")
    print(f"  错误/无法检查: {len(error_plugins)}")
    print(f"  总计: {len(all_results)}")

    # 详细列出抽象类
    if abstract_plugins:
        print("\n" + "="*80)
        print("抽象类插件详情")
        print("="*80)

        for plugin in abstract_plugins:
            print(f"\n[ABSTRACT] {plugin['class']}")
            print(f"  文件: {plugin['file']}")
            print(f"  模块: {plugin['module']}")
            print(f"  继承自ABC: {plugin['is_abc']}")
            print(f"  抽象方法: {plugin['abstract_methods']}")
            if plugin['instantiate_error']:
                print(f"  实例化错误: {plugin['instantiate_error'][:100]}")

    # 列出错误
    if error_plugins:
        print("\n" + "="*80)
        print("错误/无法检查的插件")
        print("="*80)

        for plugin in error_plugins:
            print(f"\n[ERROR] {plugin.get('file', 'unknown')}")
            print(f"  状态: {plugin['status']}")
            print(f"  错误: {plugin.get('error', 'unknown')[:150]}")

    # 结论
    print("\n" + "="*80)
    print("结论")
    print("="*80)

    if abstract_plugins:
        print(f"\n发现 {len(abstract_plugins)} 个抽象类插件:")
        for plugin in abstract_plugins:
            print(f"  - {plugin['module']}.{plugin['class']}")
        print("\n这些插件被plugin_manager跳过是正确的行为！")
        print("\n建议:")
        print("  1. 实现缺失的抽象方法")
        print("  2. 或将它们移到templates目录")
        print("  3. 或添加文档说明它们是抽象基类")
    else:
        print("\n未发现抽象类插件")

    if error_plugins:
        print(f"\n警告: {len(error_plugins)} 个插件无法检查，可能存在导入错误")


if __name__ == '__main__':
    main()
