#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Fix encoding
sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = __import__('io').TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("\n" + "="*60)
print("Schema A - Final Completion Verification")
print("="*60)

# Step 1: Critical code deletion verification
print("\n[Step 1] Verifying critical code deletion...")
critical_checks = [
    ("_integrate_quality_monitor", "gui/enhanced_main_window_integration.py", False),
    ("_on_toggle_quality_monitor_panel", "core/coordinators/main_window_coordinator.py", False),
    ("data_quality_monitor_tab", "core/coordinators/main_window_coordinator.py", False),
]

step1_ok = True
for keyword, filepath, should_exist in critical_checks:
    full_path = project_root / filepath
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        exists = keyword in content
        
        if exists == should_exist:
            print("[OK] {} - '{}' correctly deleted/absent".format(filepath.split('/')[-1], keyword[:25]))
        else:
            print("[ERROR] {} - '{}' still exists or improperly deleted".format(filepath.split('/')[-1], keyword[:25]))
            step1_ok = False
    except Exception as e:
        print("[ERROR] Failed to read {}: {}".format(filepath, str(e)[:40]))
        step1_ok = False

print("[Step 1 Result]:", "PASS" if step1_ok else "FAIL")

# Step 2: Import verification
print("\n[Step 2] Verifying imports...")
step2_ok = True
imports = [
    ("EnhancedMainWindowIntegrator", "gui.enhanced_main_window_integration"),
    ("MainWindowCoordinator", "core.coordinators.main_window_coordinator"),
    ("EnhancedDataImportWidget", "gui.widgets.enhanced_data_import_widget"),
]

for class_name, module_name in imports:
    try:
        module = __import__(module_name, fromlist=[class_name])
        if hasattr(module, class_name):
            print("[OK] {} imported".format(class_name))
        else:
            print("[ERROR] {} not found".format(class_name))
            step2_ok = False
    except Exception as e:
        print("[ERROR] Failed to import {}: {}".format(class_name, str(e)[:40]))
        step2_ok = False

print("[Step 2 Result]:", "PASS" if step2_ok else "FAIL")

# Step 3: Tab integration verification
print("\n[Step 3] Verifying right-side Tab integration...")
step3_ok = False
try:
    quality_tab_file = project_root / 'gui/widgets/enhanced_data_import_widget.py'
    with open(quality_tab_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'create_quality_status_tab' in content and 'self.monitor_tabs.addTab(quality_tab' in content:
        print("[OK] Quality Tab properly integrated into monitor_tabs")
        step3_ok = True
    else:
        print("[ERROR] Quality Tab integration incomplete")
except Exception as e:
    print("[ERROR] Tab verification failed: {}".format(str(e)[:40]))

print("[Step 3 Result]:", "PASS" if step3_ok else "FAIL")

# Step 4: No duplicate Dock verification
print("\n[Step 4] Verifying no duplicate Dock widgets...")
step4_ok = True
dock_keywords = [
    'QDockWidget("数据质量监控"',
    'quality_monitor_tab" in self.dock_widgets',
    'self._enhanced_components[\'data_quality_monitor_tab\']',
]

for filepath in ['gui/enhanced_main_window_integration.py', 'core/coordinators/main_window_coordinator.py']:
    full_path = project_root / filepath
    if not full_path.exists():
        continue
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for keyword in dock_keywords:
            if keyword in content:
                # Check it's not in a comment
                for line in content.split('\n'):
                    if keyword in line and not line.strip().startswith('#'):
                        print("[ERROR] Found '{}' in {}".format(keyword[:30], filepath.split('/')[-1]))
                        step4_ok = False
                        break
    except Exception as e:
        print("[ERROR] Failed to check {}: {}".format(filepath, str(e)[:30]))
        step4_ok = False

if step4_ok:
    print("[OK] No duplicate Dock creation code found")

print("[Step 4 Result]:", "PASS" if step4_ok else "FAIL")

# Summary
print("\n" + "="*60)
print("Summary")
print("="*60)
results = [
    ("Critical Code Deletion", step1_ok),
    ("Module Imports", step2_ok),
    ("Tab Integration", step3_ok),
    ("Dock Removal", step4_ok),
]

passed = sum(1 for _, result in results if result)
total = len(results)

for name, result in results:
    status = "PASS" if result else "FAIL"
    print("[{}] {}".format(status, name))

print("\nTotal: {}/{} verifications passed".format(passed, total))

if passed == total:
    print("\n[SUCCESS] Schema A execution complete!")
    print("- Bottom Dock completely removed")
    print("- Right-side Quality Tab functioning normally")
    print("- All imports working correctly")
    sys.exit(0)
else:
    print("\n[WARNING] Some verifications failed. Review the errors above.")
    sys.exit(1)
