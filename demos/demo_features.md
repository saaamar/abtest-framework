> Purpose: Description of features demonstrated by the demo_feature_showcase.py script
> Generated: Manually authored, maintained under version control.

================================================================================
AB FRAMEWORK - FEATURE SHOWCASE
Comprehensive demonstration of all framework capabilities
================================================================================

================================================================================
FEATURE 1: SAMPLE SIZE PLANNING
================================================================================

### 1A: Sample Size for Conversion Rate (Proportions)
--------------------------------------------------------------------------------
Scenario: Increase signup conversion from 5% to 6%

Required Sample Size:
  * Control: 8,159 users
  * Treatment: 8,159 users
  * Total: 16,318 users
  * Baseline: 5.0%
  * Expected Treatment: 6.0%

### 1B: Sample Size for Continuous Metrics (Means)
--------------------------------------------------------------------------------
Scenario: Increase average session duration from 180s to 200s

Required Sample Size:
  * Control: 289 users
  * Treatment: 289 users
  * Total: 578 users
  * Baseline: 180s
  * Standard Deviation: 60s
  * Expected Treatment: 200s

### 1C: Power Analysis
--------------------------------------------------------------------------------
Question: What power do we have with only 5,000 users?
Traceback (most recent call last):
  File "C:\Users\saaamar\repos\ab_testing\demo_feature_showcase.py", line 66, in <module>
    power = calc.calculate_power_proportion(
AttributeError: 'SampleSizeCalculator' object has no attribute 'calculate_power_proportion'
