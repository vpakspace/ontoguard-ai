"""
OntoGuard - A semantic firewall for AI agents.

OntoGuard validates agent actions against OWL ontologies to prevent
business rule violations.
"""

__version__ = "0.1.0"

from .validator import OntologyValidator, ValidationResult

__all__ = ["OntologyValidator", "ValidationResult"]
