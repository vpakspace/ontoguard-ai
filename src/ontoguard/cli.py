"""
Command-line interface for OntoGuard.

This module provides CLI commands for validating actions against OWL ontologies.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rdflib.namespace import RDF, RDFS, OWL

from ontoguard import OntologyValidator, ValidationResult

# Initialize rich console
console = Console()


def print_validation_result(result: ValidationResult, show_metadata: bool = False) -> None:
    """
    Print a validation result in a nice format.
    
    Args:
        result: The ValidationResult to display
        show_metadata: Whether to show detailed metadata
    """
    # Determine status color and icon (using ASCII-safe characters)
    if result.allowed:
        status_color = "green"
        status_icon = "[OK]"
        status_text = "[bold green]ALLOWED[/bold green]"
    else:
        status_color = "red"
        status_icon = "[X]"
        status_text = "[bold red]DENIED[/bold red]"
    
    # Create result panel
    content = f"{status_icon} {status_text}\n\n[bold]Reason:[/bold] {result.reason}"
    
    # Add suggested actions if available
    if result.suggested_actions:
        content += f"\n\n[bold]Suggested Alternatives:[/bold]"
        for action in result.suggested_actions[:5]:  # Limit to 5
            content += f"\n  - {action}"
    
    # Add metadata if requested
    if show_metadata and result.metadata:
        content += f"\n\n[bold]Metadata:[/bold]"
        context = result.metadata.get("context", {})
        if context:
            for key, value in list(context.items())[:5]:  # Show first 5
                content += f"\n  - {key}: {value}"
    
    panel = Panel(
        content.strip(),
        border_style=status_color,
        title="[bold]Validation Result[/bold]"
    )
    
    console.print(panel)


@click.group()
@click.version_option(version="0.1.0", prog_name="ontoguard")
def cli():
    """
    OntoGuard - Semantic Firewall for AI Agents
    
    Validate AI agent actions against OWL ontologies to prevent
    business rule violations.
    """
    pass


@cli.command()
@click.argument('ontology_file', type=click.Path(exists=True, path_type=Path))
@click.option('--action', '-a', required=True, help='Action to validate (e.g., "create order")')
@click.option('--entity', '-e', required=True, help='Entity type (e.g., "Order", "User")')
@click.option('--entity-id', '-i', default='', help='Entity identifier (optional)')
@click.option('--role', '-r', help='User role (e.g., "Admin", "Customer")')
@click.option('--context', '-c', help='Additional context as JSON string (optional)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed metadata')
def validate(ontology_file: Path, action: str, entity: str, entity_id: str, 
             role: Optional[str], context: Optional[str], verbose: bool):
    """
    Validate a single action against an ontology.
    
    Test whether a specific action is allowed for a given entity type
    and context according to the business rules defined in the ontology.
    
    Examples:
    
        ontoguard validate ecommerce.owl --action "create order" --entity "Order" --role "Customer"
        
        ontoguard validate ecommerce.owl -a "delete user" -e "User" -r "Admin" -v
    """
    try:
        # Load ontology
        console.print(f"[cyan]Loading ontology from:[/cyan] {ontology_file}")
        validator = OntologyValidator(str(ontology_file))
        console.print(f"[green][OK][/green] Loaded {len(validator.graph)} triples\n")
        
        # Parse context
        context_dict: Dict[str, Any] = {}
        if role:
            context_dict['role'] = role
        if context:
            try:
                import json
                context_dict.update(json.loads(context))
            except json.JSONDecodeError:
                console.print(f"[red]Error:[/red] Invalid JSON in --context option")
                sys.exit(1)
        
        # Validate action
        console.print(f"[cyan]Validating action:[/cyan] {action}")
        console.print(f"[cyan]Entity:[/cyan] {entity} (ID: {entity_id or 'N/A'})")
        if context_dict:
            console.print(f"[cyan]Context:[/cyan] {context_dict}\n")
        
        result = validator.validate(
            action=action,
            entity=entity,
            entity_id=entity_id,
            context=context_dict
        )
        
        # Display result
        print_validation_result(result, show_metadata=verbose)
        
        # Exit with appropriate code
        sys.exit(0 if result.allowed else 1)
        
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Ontology file not found: {ontology_file}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Failed to load ontology: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        if verbose:
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('ontology_file', type=click.Path(exists=True, path_type=Path))
def interactive(ontology_file: Path):
    """
    Start an interactive REPL for testing actions.
    
    Allows you to test multiple actions against the ontology without
    restarting the validator. Type 'exit' or 'quit' to end the session.
    
    Example:
    
        ontoguard interactive ecommerce.owl
    """
    try:
        # Load ontology
        console.print(f"[cyan]Loading ontology from:[/cyan] {ontology_file}")
        validator = OntologyValidator(str(ontology_file))
        console.print(f"[green][OK][/green] Loaded {len(validator.graph)} triples\n")
        
        console.print(Panel.fit(
            "[bold cyan]OntoGuard Interactive Mode[/bold cyan]\n"
            "Type 'exit' or 'quit' to end the session\n"
            "Type 'help' for available commands",
            border_style="cyan"
        ))
        console.print()
        
        while True:
            try:
                # Prompt for action
                action = Prompt.ask("[bold cyan]Action[/bold cyan]", default="").strip()
                if not action or action.lower() in ['exit', 'quit', 'q']:
                    console.print("[yellow]Exiting interactive mode...[/yellow]")
                    break
                
                if action.lower() == 'help':
                    console.print("\n[bold]Available commands:[/bold]")
                    console.print("  • exit, quit, q - Exit interactive mode")
                    console.print("  • help - Show this help message")
                    console.print("  • info - Show ontology information")
                    console.print("\n[bold]To validate an action:[/bold]")
                    console.print("  Enter the action name when prompted\n")
                    continue
                
                if action.lower() == 'info':
                    _show_ontology_info(validator)
                    continue
                
                # Prompt for entity
                entity = Prompt.ask("[bold cyan]Entity Type[/bold cyan]", default="").strip()
                if not entity:
                    console.print("[yellow]Skipping validation (no entity provided)[/yellow]\n")
                    continue
                
                # Prompt for entity ID (optional)
                entity_id = Prompt.ask("[bold cyan]Entity ID[/bold cyan] (optional)", default="").strip()
                
                # Prompt for role (optional)
                role = Prompt.ask("[bold cyan]Role[/bold cyan] (optional)", default="").strip()
                
                # Build context
                context: Dict[str, Any] = {}
                if role:
                    context['role'] = role
                
                # Additional context fields
                console.print("[dim]Enter additional context fields (press Enter to skip):[/dim]")
                while True:
                    key = Prompt.ask("  [dim]Context key[/dim] (or Enter to finish)", default="").strip()
                    if not key:
                        break
                    value = Prompt.ask(f"  [dim]Value for '{key}'[/dim]")
                    context[key] = value
                
                # Validate
                console.print()
                result = validator.validate(
                    action=action,
                    entity=entity,
                    entity_id=entity_id,
                    context=context
                )
                
                print_validation_result(result, show_metadata=True)
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]\n")
            except EOFError:
                console.print("\n[yellow]Exiting interactive mode...[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}\n")
        
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Ontology file not found: {ontology_file}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Failed to load ontology: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('ontology_file', type=click.Path(exists=True, path_type=Path))
@click.option('--detailed', '-d', is_flag=True, help='Show detailed information')
def info(ontology_file: Path, detailed: bool):
    """
    Show information about an ontology.
    
    Displays classes (entity types), actions, properties, and summary
    statistics for the loaded ontology.
    
    Example:
    
        ontoguard info ecommerce.owl
        
        ontoguard info ecommerce.owl --detailed
    """
    try:
        # Load ontology
        console.print(f"[cyan]Loading ontology from:[/cyan] {ontology_file}")
        validator = OntologyValidator(str(ontology_file))
        
        _show_ontology_info(validator, detailed=detailed)
        
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Ontology file not found: {ontology_file}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Failed to load ontology: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _show_ontology_info(validator: OntologyValidator, detailed: bool = False) -> None:
    """
    Display ontology information.
    
    Args:
        validator: The OntologyValidator instance
        detailed: Whether to show detailed information
    """
    graph = validator.graph
    if not graph:
        console.print("[red]Error:[/red] Ontology graph is not loaded")
        return
    
    console.print(f"[green][OK][/green] Loaded {len(graph)} triples\n")
    
    # Summary statistics
    summary_table = Table(title="[bold]Ontology Summary[/bold]", show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")
    
    # Count classes
    classes = list(graph.subjects(RDF.type, OWL.Class))
    summary_table.add_row("Classes", str(len(classes)))
    
    # Count object properties
    object_props = list(graph.subjects(RDF.type, OWL.ObjectProperty))
    summary_table.add_row("Object Properties", str(len(object_props)))
    
    # Count datatype properties
    datatype_props = list(graph.subjects(RDF.type, OWL.DatatypeProperty))
    summary_table.add_row("Datatype Properties", str(len(datatype_props)))
    
    # Count individuals
    individuals = list(graph.subjects(RDF.type, None))
    summary_table.add_row("Individuals", str(len(set(individuals))))
    
    # Count triples
    summary_table.add_row("Total Triples", str(len(graph)))
    
    console.print(summary_table)
    console.print()
    
    if detailed:
        # List classes
        if classes:
            classes_table = Table(title="[bold]Classes (Entity Types)[/bold]", show_header=True, header_style="bold cyan")
            classes_table.add_column("Class", style="cyan")
            classes_table.add_column("Label", style="white")
            
            for cls in classes[:20]:  # Limit to 20 for display
                labels = list(graph.objects(cls, RDFS.label))
                label = str(labels[0]) if labels else str(cls).split('#')[-1].split('/')[-1]
                cls_name = str(cls).split('#')[-1].split('/')[-1]
                classes_table.add_row(cls_name, label)
            
            if len(classes) > 20:
                classes_table.add_row("...", f"[dim](and {len(classes) - 20} more)[/dim]")
            
            console.print(classes_table)
            console.print()
        
        # List object properties
        if object_props:
            props_table = Table(title="[bold]Object Properties[/bold]", show_header=True, header_style="bold cyan")
            props_table.add_column("Property", style="cyan")
            props_table.add_column("Label", style="white")
            
            for prop in object_props[:20]:  # Limit to 20
                labels = list(graph.objects(prop, RDFS.label))
                label = str(labels[0]) if labels else str(prop).split('#')[-1].split('/')[-1]
                prop_name = str(prop).split('#')[-1].split('/')[-1]
                props_table.add_row(prop_name, label)
            
            if len(object_props) > 20:
                props_table.add_row("...", f"[dim](and {len(object_props) - 20} more)[/dim]")
            
            console.print(props_table)
            console.print()
        
        # List datatype properties
        if datatype_props:
            dt_props_table = Table(title="[bold]Datatype Properties[/bold]", show_header=True, header_style="bold cyan")
            dt_props_table.add_column("Property", style="cyan")
            dt_props_table.add_column("Label", style="white")
            
            for prop in datatype_props[:20]:  # Limit to 20
                labels = list(graph.objects(prop, RDFS.label))
                label = str(labels[0]) if labels else str(prop).split('#')[-1].split('/')[-1]
                prop_name = str(prop).split('#')[-1].split('/')[-1]
                dt_props_table.add_row(prop_name, label)
            
            if len(datatype_props) > 20:
                dt_props_table.add_row("...", f"[dim](and {len(datatype_props) - 20} more)[/dim]")
            
            console.print(dt_props_table)
            console.print()
    
    # Show action-related classes (if any)
    action_classes = []
    for cls in classes:
        labels = list(graph.objects(cls, RDFS.label))
        for label in labels:
            label_str = str(label).lower()
            if 'action' in label_str or any(keyword in label_str for keyword in ['create', 'delete', 'modify', 'process', 'cancel']):
                action_classes.append((cls, label))
    
    if action_classes:
        actions_table = Table(title="[bold]Defined Actions[/bold]", show_header=True, header_style="bold cyan")
        actions_table.add_column("Action Class", style="cyan")
        actions_table.add_column("Label", style="white")
        
        for cls, label in action_classes[:15]:  # Limit to 15
            cls_name = str(cls).split('#')[-1].split('/')[-1]
            actions_table.add_row(cls_name, str(label))
        
        if len(action_classes) > 15:
            actions_table.add_row("...", f"[dim](and {len(action_classes) - 15} more)[/dim]")
        
        console.print(actions_table)
        console.print()


if __name__ == '__main__':
    cli()
