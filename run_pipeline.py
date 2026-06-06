#!/usr/bin/env python3
"""run_pipeline.py
FinSight — Customer Behavioral Intelligence Platform

Master pipeline orchestrator that coordinates all ingestion, transformation,
feature engineering, scoring, and feedback evaluation processes sequentially.
"""

import sys
import os
import time
import subprocess
from typing import List, Tuple

# Color definitions for clean terminal outputs
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Ordered list of execution stages: (Step Name, Script Path)
PIPELINE_STAGES: List[Tuple[str, str]] = [
    ("1. Synthetic Data Generation", "pipeline/generate_data.py"),
    ("2. Data Cleaning & Transformation", "pipeline/clean_transform.py"),
    ("3. Database Schema Recreation & Ingestion", "pipeline/load_to_db.py"),
    ("4. Feature Aggregation (SQL CTEs/NTILE)", "pipeline/aggregate_features.py"),
    ("5. RFM Value Scoring & Segmentation", "scoring/rfm_engine.py"),
    ("6. Life Event Scoring & Engagement Fusion", "engagement/combined_scorer.py"),
    ("7. Spend Velocity Anomaly Detection (Z-Scores)", "scoring/velocity_detector.py"),
    ("8. Customer Priority Index Fusion", "fusion/priority_index.py"),
    ("9. Campaign Conversion & A/B Feedback Loop", "pipeline/feedback_loop.py"),
]


def run_stage(name: str, script_path: str) -> bool:
    """Executes a single pipeline stage as an isolated Python subprocess.

    Args:
        name: Visual stage descriptor.
        script_path: Workspace-relative path to the script.

    Returns:
        True if the stage completed successfully, False otherwise.
    """
    print(f"\n{BOLD}{BLUE}[STAGE] Starting {name}...{RESET}")
    print(f"Running: {script_path}")
    start_time = time.time()
    
    # Run the script using the current Python executable
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            env=env
        )
        elapsed = time.time() - start_time
        print(f"{GREEN}✓ Stage '{name}' completed successfully in {elapsed:.2f}s.{RESET}")
        return True
    except subprocess.CalledProcessError as err:
        print(f"{RED}✗ Stage '{name}' failed with exit code {err.returncode}.{RESET}")
        return False
    except Exception as err:
        print(f"{RED}✗ Stage '{name}' failed with exception: {err}{RESET}")
        return False


def run_all() -> None:
    """Coordinates and executes all pipeline stages sequentially."""
    print("=" * 60)
    print(f"    {BOLD}FinSight — Customer Behavioral Intelligence Platform{RESET}")
    print("=" * 60)
    print("Initiating full end-to-end analytics batch run...")
    
    total_start = time.time()
    results = []
    
    for name, path in PIPELINE_STAGES:
        success = run_stage(name, path)
        results.append((name, success))
        if not success:
            print(f"\n{RED}{BOLD}Pipeline execution aborted due to failures.{RESET}")
            sys.exit(1)
            
    total_elapsed = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"    {BOLD}{GREEN}FinSight End-to-End Pipeline Execution Summary{RESET}")
    print("=" * 60)
    
    for name, success in results:
        status = f"{GREEN}SUCCESS{RESET}" if success else f"{RED}FAILED{RESET}"
        print(f"- {name:<50}: {status}")
        
    print(f"\n{BOLD}Total Pipeline Elapsed Time: {total_elapsed:.2f} seconds{RESET}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all()
