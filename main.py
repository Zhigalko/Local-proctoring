"""
Root entry point for Local Proctoring System.
Delegates execution to proctoring_system.main.main().
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from proctoring_system.main import main

if __name__ == "__main__":
    main()
