This folder contains verification tooling for the A/B testing framework.

- `data_generator.py`: generates synthetic scenario data into the top-level `data/` folder.
- `ground_truth.py`: computes statistical ground truth for each scenario.
- `compare_all_packages.py`: compares multiple libraries against ground truth on scenarios 1–4.
- `tests/`: pytest-based verification tests for each library and the custom `ab_framework`.
- `SCENARIOS_EXPLAINED.md`: detailed description of all 8 scenarios.

Use `python run_full_verification.py` from the repo root to regenerate data,
run ground truth, and compare packages.
