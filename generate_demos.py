"""
Generate demo files with proper UTF-8 encoding for Windows
"""
import sys
import io
import subprocess

# Force UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_and_save(script_name, output_file):
    """Run a script and save output to file with UTF-8 encoding"""
    print(f"Generating {output_file}...")
    
    try:
        # Set PYTHONIOENCODING to UTF-8
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Write output to file with UTF-8 encoding
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write(result.stderr)
        
        print(f"✓ Created {output_file} ({len(result.stdout):,} chars)")
        return True
        
    except Exception as e:
        print(f"✗ Error creating {output_file}: {e}")
        return False

def main():
    print("=" * 80)
    print("GENERATING DEMO FILES")
    print("=" * 80)
    print()
    
    demos = [
        ("example_usage.py", "demos/demo_quick_start.txt"),
        ("example_real_world_workflow.py", "demos/demo_real_world_workflow.txt"),
        ("demo_feature_showcase.py", "demos/demo_features.md"),
        ("demo_verification_simple.py", "demos/demo_verification.txt"),
    ]
    
    success_count = 0
    for script, output in demos:
        if run_and_save(script, output):
            success_count += 1
        print()
    
    print("=" * 80)
    print(f"COMPLETE: {success_count}/{len(demos)} demos generated successfully")
    print("=" * 80)
    print()
    print("Demo files created in demos/ directory:")
    print("  • demo_quick_start.txt - Basic usage example")
    print("  • demo_real_world_workflow.txt - Complete A/A → A/B pipeline")
    print("  • demo_features.md - Feature showcase")
    print("  • demo_verification.txt - Accuracy validation")
    print()

if __name__ == '__main__':
    main()
