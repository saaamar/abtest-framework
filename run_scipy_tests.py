import sys
import os

# Change to tests directory
os.chdir('verification/tests')

# Run the test
exec(open('test_scipy_baseline.py', encoding='utf-8').read())
