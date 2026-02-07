"""
Performance benchmarks for OntologyValidator.

Validates throughput claims: >5K validations/sec on standard hardware.
Run with: pytest tests/test_benchmarks.py -v -s
"""

import time
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ontoguard import OntologyValidator


ONTOLOGY_DIR = Path(__file__).parent.parent / "examples" / "ontologies"


@pytest.fixture(params=["healthcare.owl", "ecommerce.owl", "finance.owl"])
def validator(request):
    """Create validator for each available ontology."""
    path = ONTOLOGY_DIR / request.param
    if not path.exists():
        pytest.skip(f"Ontology not found: {path}")
    return OntologyValidator(str(path)), request.param


class TestValidationThroughput:
    """Benchmark validation throughput across ontologies."""

    ITERATIONS = 10_000
    MIN_RATE = 5_000  # validations/sec

    def test_throughput_allowed(self, validator):
        """Benchmark throughput for ALLOWED validations."""
        v, name = validator
        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            v.validate("read", "PatientRecord", "p1", {"role": "Admin"})
        elapsed = time.perf_counter() - start
        rate = self.ITERATIONS / elapsed
        assert rate > self.MIN_RATE, (
            f"{name}: expected >{self.MIN_RATE} val/sec, got {rate:.0f}"
        )
        print(f"\n  {name} (allowed): {rate:,.0f} val/sec ({elapsed*1000/self.ITERATIONS:.3f} ms/val)")

    def test_throughput_denied(self, validator):
        """Benchmark throughput for DENIED validations (no matching rule)."""
        v, name = validator
        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            v.validate("delete", "NonExistentEntity", "x1", {"role": "nobody"})
        elapsed = time.perf_counter() - start
        rate = self.ITERATIONS / elapsed
        assert rate > self.MIN_RATE, (
            f"{name}: expected >{self.MIN_RATE} val/sec, got {rate:.0f}"
        )
        print(f"\n  {name} (denied): {rate:,.0f} val/sec ({elapsed*1000/self.ITERATIONS:.3f} ms/val)")
