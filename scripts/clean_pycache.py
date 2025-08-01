import os
import shutil


def clean_pycache():
    """
    递归删除当前目录及其子目录下所有的 __pycache__ 目录和 .pyc 文件。
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # 脚本在scripts目录下，所以上两级是项目根目录

    print(f"开始清理项目根目录: {project_root}")

    deleted_folders = 0
    deleted_files = 0

    for root, dirs, files in os.walk(project_root):
        # 删除 __pycache__ 目录
        if "__pycache__" in dirs:
            pycache_dir = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_dir)
                deleted_folders += 1
                print(f"  - 已删除: {pycache_dir}")
            except OSError as e:
                print(f"  - 删除失败: {pycache_dir} ({e})")

        # 删除 .pyc 文件
        for file in files:
            if file.endswith('.pyc'):
                pyc_file = os.path.join(root, file)
                try:
                    os.remove(pyc_file)
                    deleted_files += 1
                    print(f"  - 已删除: {pyc_file}")
                except OSError as e:
                    print(f"  - 删除失败: {pyc_file} ({e})")

    print("\n清理完成！")
    print(f"总共删除目录: {deleted_folders}")
    print(f"总共删除文件: {deleted_files}")


if __name__ == "__main__":
    clean_pycache()
