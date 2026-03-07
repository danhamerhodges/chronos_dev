"""Canonical processing enums for Phase 3 packets."""

from __future__ import annotations

from enum import StrEnum


class ReproducibilityMode(StrEnum):
    PERCEPTUAL_EQUIVALENCE = "perceptual_equivalence"
    DETERMINISTIC = "deterministic"
    BIT_IDENTICAL = "bit_identical"
