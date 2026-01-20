#!/usr/bin/env python3
"""
Basic Usage Example for OntoGuard

This script demonstrates how to use OntoGuard to validate AI agent actions
against the e-commerce ontology. It shows various scenarios including
role-based permissions, business rule enforcement, and constraint validation.

Run this script with:
    python examples/basic_usage.py
"""

import sys
from pathlib import Path

# Add src to path so we can import ontoguard
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ontoguard import OntologyValidator, ValidationResult
from rich.console import Console
from rich.panel import Panel

# Initialize rich console for beautiful output
# Configure console to handle encoding issues on Windows
console = Console(force_terminal=True, legacy_windows=False)


def print_result(scenario_name: str, result: ValidationResult, expected: str) -> None:
    """
    Print a validation result in a nice format.
    
    Args:
        scenario_name: Name/description of the scenario being tested
        result: The ValidationResult from the validator
        expected: Expected outcome ("ALLOW" or "DENY")
    """
    # Determine if result matches expectation
    matches = (result.allowed and expected == "ALLOW") or (not result.allowed and expected == "DENY")
    
    # Create status indicator (using ASCII-safe characters)
    if result.allowed:
        status_icon = "[green][OK][/green]"
        status_text = "[green]ALLOWED[/green]"
    else:
        status_icon = "[red][X][/red]"
        status_text = "[red]DENIED[/red]"
    
    # Check if matches expectation
    if matches:
        expectation_status = "[green][OK] Expected[/green]"
    else:
        expectation_status = "[red][X] Unexpected[/red]"
    
    # Create a panel with the result
    content = f"""
{status_icon} Result: {status_text} ({expectation_status})

[bold]Reason:[/bold] {result.reason}
"""
    
    # Add suggested actions if available
    if result.suggested_actions:
        content += f"\n[bold]Suggested Alternatives:[/bold]\n"
        for action in result.suggested_actions[:3]:  # Show up to 3
            content += f"  - {action}\n"
    
    # Add metadata summary if available
    if result.metadata:
        context = result.metadata.get("context", {})
        if context:
            content += f"\n[bold]Context:[/bold]\n"
            for key, value in list(context.items())[:3]:  # Show first 3 context items
                content += f"  - {key}: {value}\n"
    
    # Create panel with appropriate border color
    border_color = "green" if matches else "red"
    panel = Panel(
        content.strip(),
        title=f"[bold]{scenario_name}[/bold]",
        border_style=border_color,
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()  # Empty line for spacing


def main():
    """Main function demonstrating OntoGuard usage."""
    
    # Print header
    console.print(Panel.fit(
        "[bold cyan]OntoGuard - Semantic Firewall for AI Agents[/bold cyan]\n"
        "E-Commerce Ontology Validation Examples",
        border_style="cyan"
    ))
    console.print()
    
    # Step 1: Load the ontology
    console.print("[bold]Step 1:[/bold] Loading e-commerce ontology...")
    ontology_path = Path(__file__).parent / "ontologies" / "ecommerce.owl"
    
    if not ontology_path.exists():
        console.print(f"[red]Error:[/red] Ontology file not found at {ontology_path}")
        console.print("Please ensure the ecommerce.owl file exists in examples/ontologies/")
        sys.exit(1)
    
    try:
        validator = OntologyValidator(str(ontology_path))
        console.print(f"[green][OK][/green] Successfully loaded ontology from {ontology_path}")
        console.print(f"   Loaded {len(validator.graph)} triples\n")
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load ontology: {e}")
        sys.exit(1)
    
    # Step 2: Run validation scenarios
    console.print("[bold]Step 2:[/bold] Running validation scenarios...\n")
    
    # Scenario 1: Admin deleting a user (should ALLOW)
    # This demonstrates Rule 1: Only Admins can delete Users
    console.print("[bold cyan]Scenario 1:[/bold cyan] Admin attempting to delete a user")
    result1 = validator.validate(
        action="delete user",
        entity="User",
        entity_id="user_123",
        context={
            "role": "Admin",
            "user_id": "admin_001",
            "target_user_id": "user_123"
        }
    )
    print_result(
        "Admin deleting a user",
        result1,
        "ALLOW"
    )
    
    # Scenario 2: Customer deleting a user (should DENY)
    # This demonstrates Rule 1: Only Admins can delete Users
    # Customers should not have permission to delete users
    console.print("[bold cyan]Scenario 2:[/bold cyan] Customer attempting to delete a user")
    result2 = validator.validate(
        action="delete user",
        entity="User",
        entity_id="user_456",
        context={
            "role": "Customer",
            "user_id": "customer_001",
            "target_user_id": "user_456"
        }
    )
    print_result(
        "Customer deleting a user",
        result2,
        "DENY"
    )
    
    # Scenario 3: Manager processing $500 refund (should ALLOW)
    # This demonstrates Rule 2: Refunds over $1000 require Manager approval
    # A $500 refund is below the threshold, so it should be allowed
    console.print("[bold cyan]Scenario 3:[/bold cyan] Manager processing a $500 refund")
    result3 = validator.validate(
        action="process refund",
        entity="Refund",
        entity_id="refund_001",
        context={
            "role": "Manager",
            "user_id": "manager_001",
            "refund_amount": 500.00,
            "order_id": "order_123"
        }
    )
    print_result(
        "Manager processing $500 refund",
        result3,
        "ALLOW"
    )
    
    # Scenario 4: Customer processing $2000 refund (should DENY - needs manager)
    # This demonstrates Rule 2: Refunds over $1000 require Manager approval
    # A $2000 refund exceeds the threshold, and a Customer doesn't have Manager role
    console.print("[bold cyan]Scenario 4:[/bold cyan] Customer attempting to process a $2000 refund")
    result4 = validator.validate(
        action="process refund",
        entity="Refund",
        entity_id="refund_002",
        context={
            "role": "Customer",
            "user_id": "customer_002",
            "refund_amount": 2000.00,
            "order_id": "order_456",
            "required_role": "Manager"  # This triggers the constraint check
        }
    )
    print_result(
        "Customer processing $2000 refund (requires Manager approval)",
        result4,
        "DENY"
    )
    
    # Scenario 5: Cancelling an order within 24 hours (should ALLOW)
    # This demonstrates Rule 3: Orders can only be cancelled within 24 hours
    # An order placed 5 hours ago should be cancellable
    console.print("[bold cyan]Scenario 5:[/bold cyan] Customer cancelling an order placed 5 hours ago")
    result5 = validator.validate(
        action="cancel order",
        entity="Order",
        entity_id="order_789",
        context={
            "role": "Customer",
            "user_id": "customer_003",
            "order_time": "2024-01-01T10:00:00Z",
            "current_time": "2024-01-01T15:00:00Z",  # 5 hours later
            "hours_since_order": 5
        }
    )
    print_result(
        "Cancelling order within 24 hours (5 hours old)",
        result5,
        "ALLOW"
    )
    
    # Scenario 6: Cancelling an order after 48 hours (should DENY)
    # This demonstrates Rule 3: Orders can only be cancelled within 24 hours
    # An order placed 48 hours ago exceeds the 24-hour limit
    console.print("[bold cyan]Scenario 6:[/bold cyan] Customer attempting to cancel an order placed 48 hours ago")
    result6 = validator.validate(
        action="cancel order",
        entity="Order",
        entity_id="order_999",
        context={
            "role": "Customer",
            "user_id": "customer_004",
            "order_time": "2024-01-01T10:00:00Z",
            "current_time": "2024-01-03T10:00:00Z",  # 48 hours later
            "hours_since_order": 48
        }
    )
    print_result(
        "Cancelling order after 48 hours (exceeds 24h limit)",
        result6,
        "DENY"
    )
    
    # Step 3: Demonstrate explain_denial for a denied action
    console.print("[bold]Step 3:[/bold] Getting detailed explanation for a denied action...\n")
    
    explanation = validator.explain_denial(
        action="delete user",
        entity="User",
        context={"role": "Customer"}
    )
    
    # Remove emoji characters that may cause encoding issues on Windows
    # Replace common emojis with ASCII equivalents
    explanation_clean = explanation.replace('❌', '[X]').replace('📋', '[Info]').replace('💡', '[Tip]')
    
    console.print(Panel(
        explanation_clean,
        title="[bold]Detailed Denial Explanation[/bold]",
        border_style="yellow"
    ))
    console.print()
    
    # Step 4: Query allowed actions
    console.print("[bold]Step 4:[/bold] Querying allowed actions for different entities...\n")
    
    # Query allowed actions for Order
    order_actions = validator.get_allowed_actions("Order", {})
    console.print(f"[bold]Allowed actions for 'Order':[/bold] {len(order_actions)} found")
    if order_actions:
        for action in order_actions[:5]:  # Show first 5
            console.print(f"  - {action}")
    console.print()
    
    # Query allowed actions for User
    user_actions = validator.get_allowed_actions("User", {})
    console.print(f"[bold]Allowed actions for 'User':[/bold] {len(user_actions)} found")
    if user_actions:
        for action in user_actions[:5]:  # Show first 5
            console.print(f"  - {action}")
    console.print()
    
    # Summary
    console.print(Panel.fit(
        "[bold green][OK][/bold green] All scenarios completed successfully!\n\n"
        "This example demonstrated:\n"
        "  - Role-based access control (Admin vs Customer)\n"
        "  - Business rule enforcement (refund thresholds)\n"
        "  - Temporal constraints (24-hour cancellation window)\n"
        "  - Detailed denial explanations\n"
        "  - Querying allowed actions",
        border_style="green",
        title="[bold]Summary[/bold]"
    ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
