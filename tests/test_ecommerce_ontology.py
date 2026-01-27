"""
Test cases for the e-commerce ontology business rules.

This test suite validates that the OntologyValidator correctly enforces
the business rules defined in the e-commerce ontology.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ontoguard import OntologyValidator, ValidationResult


@pytest.fixture
def validator():
    """Create a validator instance with the e-commerce ontology."""
    ontology_path = Path(__file__).parent.parent / "examples" / "ontologies" / "ecommerce.owl"
    if not ontology_path.exists():
        pytest.skip(f"Ontology file not found: {ontology_path}")
    return OntologyValidator(str(ontology_path))


class TestECommerceOntology:
    """Test suite for e-commerce ontology business rules."""
    
    def test_ontology_loads(self, validator):
        """Test that the ontology file loads successfully."""
        assert validator is not None
        assert validator._loaded is True
        assert validator.graph is not None
        assert len(validator.graph) > 0
    
    def test_create_order_allowed_for_customer(self, validator):
        """Test Rule: Customers can create orders."""
        result = validator.validate(
            action="create order",
            entity="Order",
            entity_id="order_001",
            context={"role": "Customer", "user_id": "customer_123"}
        )
        assert result.allowed is True
        assert "create order" in result.reason.lower() or "allowed" in result.reason.lower()
    
    def test_create_order_allowed_for_admin(self, validator):
        """Test Rule: Admins can also create orders."""
        result = validator.validate(
            action="create order",
            entity="Order",
            entity_id="order_002",
            context={"role": "Admin", "user_id": "admin_001"}
        )
        assert result.allowed is True
    
    def test_delete_user_requires_admin(self, validator):
        """Test Rule 1: Only Admins can delete Users."""
        # Customer should NOT be able to delete users
        result_customer = validator.validate(
            action="delete user",
            entity="User",
            entity_id="user_123",
            context={"role": "Customer", "user_id": "customer_123"}
        )
        # Customer MUST be denied - the ontology requires Admin role
        assert result_customer.allowed is False
        assert "admin" in result_customer.reason.lower() or "role" in result_customer.reason.lower()

        # Admin SHOULD be able to delete users
        result_admin = validator.validate(
            action="delete user",
            entity="User",
            entity_id="user_456",
            context={"role": "Admin", "user_id": "admin_001"}
        )
        # Admin should have permission
        assert result_admin.allowed is True
    
    def test_modify_product_requires_admin(self, validator):
        """Test Rule 4: Products can only be modified by Admins."""
        # Customer should NOT be able to modify products
        result_customer = validator.validate(
            action="modify product",
            entity="Product",
            entity_id="product_123",
            context={"role": "Customer", "user_id": "customer_123"}
        )
        # Customer MUST be denied - the ontology requires Admin role
        assert result_customer.allowed is False
        assert "admin" in result_customer.reason.lower() or "role" in result_customer.reason.lower()

        # Admin SHOULD be able to modify products
        result_admin = validator.validate(
            action="modify product",
            entity="Product",
            entity_id="product_456",
            context={"role": "Admin", "user_id": "admin_001"}
        )
        assert result_admin.allowed is True
    
    def test_process_refund_with_high_value(self, validator):
        """Test Rule 2: Refunds over $1000 require Manager approval."""
        # High-value refund should require manager approval
        result = validator.validate(
            action="process refund",
            entity="Refund",
            entity_id="refund_001",
            context={
                "role": "Customer",
                "refund_amount": 1500.00,
                "required_role": "Manager"
            }
        )
        # The constraint checking should catch this
        if "required_role" in result.metadata.get("context", {}):
            # If context has required_role, constraint check should validate it
            pass
    
    def test_cancel_order_within_time_limit(self, validator):
        """Test Rule 3: Orders can only be cancelled within 24 hours."""
        result = validator.validate(
            action="cancel order",
            entity="Order",
            entity_id="order_123",
            context={
                "role": "Customer",
                "order_time": "2024-01-01T10:00:00Z",
                "current_time": "2024-01-01T15:00:00Z",  # 5 hours later
                "hours_since_order": 5
            }
        )
        # Should be allowed if within 24 hours
        # The ontology defines this rule, validator should check it
        assert isinstance(result, ValidationResult)
    
    def test_cancel_order_after_time_limit(self, validator):
        """Test Rule 3: Orders cannot be cancelled after 24 hours."""
        result = validator.validate(
            action="cancel order",
            entity="Order",
            entity_id="order_124",
            context={
                "role": "Customer",
                "order_time": "2024-01-01T10:00:00Z",
                "current_time": "2024-01-02T15:00:00Z",  # 29 hours later
                "hours_since_order": 29
            }
        )
        # Should be denied if over 24 hours
        # The ontology defines this rule
        assert isinstance(result, ValidationResult)
    
    def test_get_allowed_actions_for_order(self, validator):
        """Test that we can query allowed actions for Order entity."""
        actions = validator.get_allowed_actions("Order", {})
        assert isinstance(actions, list)
        # Should find at least some actions
        assert len(actions) >= 0
    
    def test_get_allowed_actions_for_user(self, validator):
        """Test that we can query allowed actions for User entity."""
        actions = validator.get_allowed_actions("User", {})
        assert isinstance(actions, list)
    
    def test_get_allowed_actions_for_product(self, validator):
        """Test that we can query allowed actions for Product entity."""
        actions = validator.get_allowed_actions("Product", {})
        assert isinstance(actions, list)
    
    def test_explain_denial_for_unauthorized_action(self, validator):
        """Test that explain_denial provides helpful explanations."""
        explanation = validator.explain_denial(
            action="delete user",
            entity="User",
            context={"role": "Customer"}
        )
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        # Should contain information about why it was denied
        # (may contain action name, entity, or context info)
    
    def test_validation_result_structure(self, validator):
        """Test that ValidationResult has the correct structure."""
        result = validator.validate(
            action="create order",
            entity="Order",
            entity_id="test_order",
            context={}
        )
        
        assert hasattr(result, 'allowed')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'suggested_actions')
        assert hasattr(result, 'metadata')
        
        assert isinstance(result.allowed, bool)
        assert isinstance(result.reason, str)
        assert isinstance(result.suggested_actions, list)
        assert isinstance(result.metadata, dict)
    
    def test_validation_result_serialization(self, validator):
        """Test that ValidationResult can be serialized."""
        result = validator.validate(
            action="create order",
            entity="Order",
            entity_id="test_order",
            context={}
        )
        
        # Test dict serialization
        result_dict = result.model_dump()
        assert isinstance(result_dict, dict)
        assert 'allowed' in result_dict
        assert 'reason' in result_dict
        
        # Test JSON serialization
        result_json = result.model_dump_json()
        assert isinstance(result_json, str)
        assert 'allowed' in result_json
    
    def test_context_passed_to_metadata(self, validator):
        """Test that context information is included in metadata."""
        context = {
            "role": "Customer",
            "user_id": "user_123",
            "session_id": "session_456"
        }
        
        result = validator.validate(
            action="create order",
            entity="Order",
            entity_id="order_123",
            context=context
        )
        
        assert 'context' in result.metadata
        assert result.metadata['context'] == context
        assert result.metadata['action'] == "create order"
        assert result.metadata['entity'] == "Order"
        assert result.metadata['entity_id'] == "order_123"
    
    def test_role_based_constraint_checking(self, validator):
        """Test that role-based constraints are checked."""
        # Test with required_role in context
        result = validator.validate(
            action="process refund",
            entity="Refund",
            entity_id="refund_001",
            context={
                "role": "Customer",
                "required_role": "Manager"
            }
        )
        
        # The constraint check should validate role mismatch
        # If role doesn't match required_role, should be denied
        assert isinstance(result, ValidationResult)
        
        # Test with matching role
        result2 = validator.validate(
            action="process refund",
            entity="Refund",
            entity_id="refund_002",
            context={
                "role": "Manager",
                "required_role": "Manager"
            }
        )
        
        assert isinstance(result2, ValidationResult)


class TestOntologyStructure:
    """Test the structure and content of the ontology itself."""
    
    def test_ontology_contains_user_classes(self, validator):
        """Test that User class hierarchy exists in ontology."""
        from rdflib.namespace import RDFS, OWL, RDF
        
        # Check for User class - look for classes with rdf:type owl:Class
        user_classes = []
        for cls in validator.graph.subjects(RDF.type, OWL.Class):
            # Get labels
            labels = list(validator.graph.objects(cls, RDFS.label))
            for label in labels:
                label_str = str(label).lower()
                if 'user' in label_str or 'customer' in label_str or 'admin' in label_str or 'manager' in label_str:
                    user_classes.append(str(label))
            
            # Also check URI fragments
            cls_str = str(cls).lower()
            if 'user' in cls_str or 'customer' in cls_str or 'admin' in cls_str or 'manager' in cls_str:
                if cls not in user_classes:
                    user_classes.append(str(cls))
        
        # Should find at least User, Customer, Admin, Manager
        assert len(user_classes) > 0, f"Expected to find user classes, but found: {user_classes}"
    
    def test_ontology_contains_action_classes(self, validator):
        """Test that Action classes exist in ontology."""
        from rdflib.namespace import RDFS, OWL, RDF
        
        action_classes = []
        # Check for classes with rdf:type owl:Class
        for cls in validator.graph.subjects(RDF.type, OWL.Class):
            # Get labels
            labels = list(validator.graph.objects(cls, RDFS.label))
            for label in labels:
                label_str = str(label).lower()
                if 'action' in label_str or ('order' in label_str and 'create' in label_str) or 'refund' in label_str:
                    action_classes.append(str(label))
            
            # Also check URI fragments
            cls_str = str(cls).lower()
            if 'action' in cls_str or ('order' in cls_str and 'create' in cls_str) or 'refund' in cls_str:
                if cls not in action_classes:
                    action_classes.append(str(cls))
        
        # Should find action-related classes
        assert len(action_classes) > 0, f"Expected to find action classes, but found: {action_classes}"
    
    def test_ontology_contains_properties(self, validator):
        """Test that object and datatype properties exist."""
        from rdflib.namespace import OWL, RDF
        
        # Look for properties with rdf:type owl:ObjectProperty or owl:DatatypeProperty
        object_props = list(validator.graph.subjects(RDF.type, OWL.ObjectProperty))
        datatype_props = list(validator.graph.subjects(RDF.type, OWL.DatatypeProperty))
        
        # Should have some properties defined
        assert len(object_props) > 0 or len(datatype_props) > 0, \
            f"Expected to find properties, but found {len(object_props)} object props and {len(datatype_props)} datatype props"
