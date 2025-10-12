import os
import shutil

old_name = "strategies/strategy_adapters_full.py"
new_name = "strategies/adj_vwap_strategies.py"

if os.path.exists(old_name):
    shutil.copy(old_name, new_name)
    print(f"Copied {old_name} -> {new_name}")
else:
    print(f"File {old_name} not found")

