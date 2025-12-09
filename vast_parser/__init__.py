"""
VAST Parser Package

Production-ready VAST parser with backward compatibility,
XPath filtering, sorting, and configuration support.
"""

from vast_parser.parser import EnhancedVASTParser, MergeStrategy, VASTParser, XPathRule


__version__ = "1.0.0"
__author__ = "VAST Enhancement Team"

__all__ = [
    "VASTParser",
    "EnhancedVASTParser",
    "MergeStrategy",
    "XPathRule",
]
