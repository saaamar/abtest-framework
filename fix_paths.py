import re

# Read the file
with open('verification/tests/test_scipy_baseline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences of pd.read_csv("data/ with pd.read_csv("../data/
content = re.sub(r'pd\.read_csv\("data/', 'pd.read_csv("../data/', content)

# Write back
with open('verification/tests/test_scipy_baseline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all paths in test_scipy_baseline.py")
