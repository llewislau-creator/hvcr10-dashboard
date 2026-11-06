"""Ensure one quarantined ticker cannot block 19 valid tickers; systemic outages still fail."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from update import require_coverage
assert require_coverage(20,20)==100
assert require_coverage(19,20)==95
assert require_coverage(18,20)==90
for n in (0,10,17):
    try:require_coverage(n,20)
    except RuntimeError:pass
    else:raise AssertionError("Low coverage must block report")
print("coverage tests passed")
