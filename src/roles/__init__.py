# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Role Intelligence Module
Per-round dynamic role detection.
"""

from .classifier import (
    RoleType,
    RoleClassifier,
    RoleAssignment,
    classify_roles,
    export_roles_json,
)

__all__ = [
    'RoleType',
    'RoleClassifier', 
    'RoleAssignment',
    'classify_roles',
    'export_roles_json',
]
