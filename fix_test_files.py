import re

files = ['verification/tests/test_abexp.py', 'verification/tests/test_owl.py']

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove duplicate if __name__ blocks
    content = re.sub(r'== "__main__":.*$', '', content, flags=re.DOTALL)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

print("Done!")
