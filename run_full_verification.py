"""Run complete end-to-end verification pipeline"""
import subprocess
import sys
import os

print("="*70)
print("COMPLETE END-TO-END VERIFICATION PIPELINE")
print("="*70)

# Get absolute paths
root_dir = os.path.abspath(".")
venv_python = os.path.join(root_dir, "venv", "Scripts", "python.exe")

steps = [
    ("Step 1: Generate Data (8 scenarios)", [venv_python, "data_generator.py"], os.path.join(root_dir, "verification")),
    ("Step 2: Calculate Ground Truth", [venv_python, "ground_truth.py"], os.path.join(root_dir, "verification")),
    ("Step 3: Run Package Comparison", [venv_python, "compare_all_packages.py"], os.path.join(root_dir, "verification")),
]

for step_name, cmd, cwd in steps:
    print(f"\n{'='*70}")
    print(f"{step_name}")
    print("="*70)
    
    result = subprocess.run(cmd, capture_output=False, cwd=cwd)
    
    if result.returncode != 0:
        print(f"\n❌ {step_name} FAILED!")
        sys.exit(1)
    
    print(f"\n✅ {step_name} completed successfully")

print("\n" + "="*70)
print("✅ COMPLETE END-TO-END VERIFICATION SUCCESSFUL!")
print("="*70)
