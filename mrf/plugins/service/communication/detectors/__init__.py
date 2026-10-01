"""Detectors for the client technologies a call can be stated with.

The registry is the only place a technology has to be named. A new detector is
a module of its own plus an entry here, so nothing else changes for it.
"""

from mrf.plugins.service.communication.detectors.detector import (
    ClientDetector,
    DetectionContext,
    Evidence,
    ServiceCall,
)
from mrf.plugins.service.communication.detectors.feign import FeignDetector
from mrf.plugins.service.communication.detectors.rest_template import (
    RestClientDetector,
)

DETECTORS: list[ClientDetector] = [FeignDetector(), RestClientDetector()]

__all__ = [
    "DETECTORS",
    "ClientDetector",
    "DetectionContext",
    "Evidence",
    "ServiceCall",
]
