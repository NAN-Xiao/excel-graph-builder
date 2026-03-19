#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关系发现模块
"""

from .base import RelationDiscoveryStrategy
from .containment import ContainmentDiscovery
from .abbreviation import AbbreviationDiscovery
from .transitive import TransitiveDiscovery
from .feedback import FeedbackManager
from .naming_convention import NamingConventionDiscovery
from .pack_array import PackArrayDiscovery
from .game_dictionary import (
    GAME_ABBREVIATIONS, DOMAIN_KEYWORDS,
    DOMAIN_CLASSIFICATION_RULES, DOMAIN_COLORS,
    lookup_abbreviation, classify_table_domain, classify_domain,
    expand_column_name,
)

__all__ = [
    'RelationDiscoveryStrategy',
    'ContainmentDiscovery',
    'AbbreviationDiscovery',
    'TransitiveDiscovery',
    'FeedbackManager',
    'NamingConventionDiscovery',
    'PackArrayDiscovery',
    'GAME_ABBREVIATIONS',
    'DOMAIN_KEYWORDS',
    'DOMAIN_CLASSIFICATION_RULES',
    'DOMAIN_COLORS',
    'lookup_abbreviation',
    'classify_table_domain',
    'classify_domain',
    'expand_column_name',
]
