"""Fix all path inconsistencies"""

# Fix ground_truth.py
with open('verification/ground_truth.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('verification/data/', 'data/')
with open('verification/ground_truth.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ Fixed ground_truth.py")

# Fix test_abexp.py
with open('verification/tests/test_abexp.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('data/', '../data/')
with open('verification/tests/test_abexp.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ Fixed test_abexp.py")

# Fix test_owl.py
with open('verification/tests/test_owl.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('data/', '../data/')
with open('verification/tests/test_owl.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ Fixed test_owl.py")

# Fix test_py_ab_testing.py if it exists
try:
    with open('verification/tests/test_py_ab_testing.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if 'pd.read_csv("data/' in content:
        content = content.replace('data/', '../data/')
        with open('verification/tests/test_py_ab_testing.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Fixed test_py_ab_testing.py")
    else:
        print("✓ test_py_ab_testing.py already has correct paths")
except Exception as e:
    print(f"⚠ test_py_ab_testing.py: {e}")

print("\n✅ All paths fixed!")
print("\nPath convention:")
print("  - verification/ground_truth.py    → uses 'data/...'")
print("  - verification/tests/test_*.py    → uses '../data/...'")
print("  - All scripts run from verification/ directory")
