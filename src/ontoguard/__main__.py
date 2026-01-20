"""
Entry point for running OntoGuard as a module.

This allows OntoGuard to be run as:
    python -m ontoguard

Instead of:
    python -m ontoguard.cli
"""

from ontoguard.cli import cli

if __name__ == '__main__':
    cli()
