"""Detectors for the technologies an interaction can be stated with.

Two registries, because the two kinds of interaction are two kinds of fact: a
call has a scheme, a verb and a path, a channel has a queue and a broker. A new
technology is a module of its own plus an entry in the registry it belongs to,
so nothing else changes for it.
"""

from mrf.plugins.service.communication.detectors.detector import (
    ClientDetector,
    DetectionContext,
    Evidence,
    MessageChannel,
    MessagingDetector,
    ServiceCall,
)
from mrf.plugins.service.communication.detectors.feign import FeignDetector
from mrf.plugins.service.communication.detectors.jms import JmsDetector
from mrf.plugins.service.communication.detectors.rest_template import (
    RestClientDetector,
)

DETECTORS: list[ClientDetector] = [FeignDetector(), RestClientDetector()]

MESSAGING_DETECTORS: list[MessagingDetector] = [JmsDetector()]

__all__ = [
    "DETECTORS",
    "MESSAGING_DETECTORS",
    "ClientDetector",
    "DetectionContext",
    "Evidence",
    "MessageChannel",
    "MessagingDetector",
    "ServiceCall",
]
