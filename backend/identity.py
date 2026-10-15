"""Canonical identity helpers shared by local testing auth and seed validation."""

from __future__ import annotations


def canonicalize_name(value: object) -> str:
    """Case-fold and trim display-name input without changing stored display text."""
    return value.strip().casefold() if isinstance(value, str) else ""


def canonicalize_user_id(value: object) -> str:
    """Trim and case-fold IDs; preserve internal whitespace and punctuation."""
    return value.strip().casefold() if isinstance(value, str) else ""


def canonicalize_role(value: object) -> str:
    """Normalize role casing and the visible Teacher alias."""
    role = value.strip().upper() if isinstance(value, str) else ""
    return "FACULTY" if role == "TEACHER" else role
