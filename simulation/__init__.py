"""
Simulation package for market maker strategies.
Contains core simulation logic and result processing.
"""

from .executor import execute_simulation
from .results import process_results

__all__ = [
    'execute_simulation',
    'process_results',
]