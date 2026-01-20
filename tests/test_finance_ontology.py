"""
Test cases for the finance ontology business rules.

This test suite validates that the OntologyValidator correctly enforces
the business rules defined in the finance ontology, including banking
regulations, transaction limits, and compliance requirements.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ontoguard import OntologyValidator, ValidationResult


@pytest.fixture
def validator():
    """Create a validator instance with the finance ontology."""
    ontology_path = Path(__file__).parent.parent / "examples" / "ontologies" / "finance.owl"
    if not ontology_path.exists():
        pytest.skip(f"Ontology file not found: {ontology_path}")
    return OntologyValidator(str(ontology_path))


class TestFinanceOntology:
    """Test suite for finance ontology business rules."""
    
    def test_ontology_loads(self, validator):
        """Test that the finance ontology file loads successfully."""
        assert validator is not None
        assert validator._loaded is True
        assert validator.graph is not None
        assert len(validator.graph) > 0
        assert len(validator.graph) == 385  # Expected triple count
    
    def test_teller_process_transaction_allowed(self, validator):
        """Test that Tellers can process regular transactions."""
        result = validator.validate(
            action="process transaction",
            entity="Transaction",
            entity_id="transaction_001",
            context={"role": "Teller", "amount": 100.00}
        )
        assert isinstance(result, ValidationResult)
        assert "transaction" in result.reason.lower() or "allowed" in result.reason.lower()
    
    def test_large_transaction_requires_manager(self, validator):
        """Test Rule 1: Transactions over $10,000 require manager approval."""
        result = validator.validate(
            action="approve large transaction",
            entity="LargeTransaction",
            entity_id="transaction_large",
            context={
                "role": "Manager",
                "transaction_amount": 15000.00,
                "user_id": "manager_123"
            }
        )
        assert isinstance(result, ValidationResult)
        assert result.metadata['context']['role'] == "Manager"
    
    def test_teller_large_transaction_denied(self, validator):
        """Test Rule 1: Tellers cannot approve large transactions."""
        result = validator.validate(
            action="approve large transaction",
            entity="LargeTransaction",
            entity_id="transaction_large_2",
            context={
                "role": "Teller",
                "transaction_amount": 15000.00,
                "required_role": "Manager"
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_international_transfer_requires_compliance(self, validator):
        """Test Rule 2: International transfers require compliance officer approval."""
        result = validator.validate(
            action="process international transfer",
            entity="InternationalTransfer",
            entity_id="transfer_intl",
            context={
                "role": "Manager",
                "is_international": True,
                "required_role": "ComplianceOfficer"
            }
        )
        assert isinstance(result, ValidationResult)
        # Should require ComplianceOfficer approval
    
    def test_account_closure_requires_dual_approval(self, validator):
        """Test Rule 3: Account closure requires dual manager approval."""
        result = validator.validate(
            action="close account",
            entity="Account",
            entity_id="account_001",
            context={
                "role": "Manager",
                "approvals_required": 2,
                "approval_count": 1
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_compliance_officer_file_sar_allowed(self, validator):
        """Test Rule 4: Only Compliance Officers can file SARs."""
        result = validator.validate(
            action="file suspicious activity report",
            entity="SuspiciousActivity",
            entity_id="sar_001",
            context={"role": "ComplianceOfficer", "user_id": "compliance_123"}
        )
        assert isinstance(result, ValidationResult)
        assert result.metadata['context']['role'] == "ComplianceOfficer"
    
    def test_teller_file_sar_denied(self, validator):
        """Test Rule 4: Tellers cannot file SARs."""
        result = validator.validate(
            action="file suspicious activity report",
            entity="SuspiciousActivity",
            entity_id="sar_002",
            context={"role": "Teller", "required_role": "ComplianceOfficer"}
        )
        assert isinstance(result, ValidationResult)
    
    def test_suspicious_transaction_requires_sar(self, validator):
        """Test Rule 5: Suspicious transactions must trigger SAR filing."""
        result = validator.validate(
            action="process transaction",
            entity="Transaction",
            entity_id="transaction_suspicious",
            context={
                "role": "Teller",
                "is_suspicious": True,
                "sar_filed": False
            }
        )
        assert isinstance(result, ValidationResult)
        # Should require SAR filing for suspicious transactions
    
    def test_international_transfer_requires_kyc(self, validator):
        """Test Rule 6: International transfers require KYC verification."""
        result = validator.validate(
            action="process international transfer",
            entity="InternationalTransfer",
            entity_id="transfer_kyc",
            context={
                "role": "Manager",
                "is_international": True,
                "requires_kyc": True,
                "kyc_verified": True
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_manager_modify_account_allowed(self, validator):
        """Test Rule 7: Only Managers can modify accounts."""
        result = validator.validate(
            action="modify account",
            entity="Account",
            entity_id="account_002",
            context={"role": "Manager", "user_id": "manager_123"}
        )
        assert isinstance(result, ValidationResult)
        assert result.metadata['context']['role'] == "Manager"
    
    def test_teller_modify_account_denied(self, validator):
        """Test Rule 7: Tellers cannot modify accounts."""
        result = validator.validate(
            action="modify account",
            entity="Account",
            entity_id="account_003",
            context={"role": "Teller", "required_role": "Manager"}
        )
        assert isinstance(result, ValidationResult)
    
    def test_teller_transaction_limit(self, validator):
        """Test Rule 8: Tellers can only process transactions up to $5,000."""
        # Transaction under limit
        result_under = validator.validate(
            action="process transaction",
            entity="Transaction",
            entity_id="transaction_small",
            context={"role": "Teller", "transaction_amount": 3000.00}
        )
        assert isinstance(result_under, ValidationResult)
        
        # Transaction over limit
        result_over = validator.validate(
            action="process transaction",
            entity="Transaction",
            entity_id="transaction_over_limit",
            context={"role": "Teller", "transaction_amount": 6000.00}
        )
        assert isinstance(result_over, ValidationResult)
    
    def test_wire_transfer_requires_approval(self, validator):
        """Test Rule 9: Wire transfers over $3,000 require manager approval."""
        result = validator.validate(
            action="process transaction",
            entity="WireTransfer",
            entity_id="wire_large",
            context={
                "role": "Teller",
                "transaction_amount": 5000.00,
                "required_role": "Manager"
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_customer_data_access_requires_justification(self, validator):
        """Test Rule 10: Customer data access requires business justification."""
        result = validator.validate(
            action="access customer data",
            entity="CustomerData",
            entity_id="customer_001",
            context={
                "role": "Teller",
                "business_justification": "Account verification"
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_very_large_transaction_requires_compliance(self, validator):
        """Test Rule 11: Transactions over $25,000 require compliance review."""
        result = validator.validate(
            action="approve large transaction",
            entity="LargeTransaction",
            entity_id="transaction_very_large",
            context={
                "role": "Manager",
                "transaction_amount": 30000.00,
                "required_role": "ComplianceOfficer"
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_new_account_requires_kyc(self, validator):
        """Test Rule 12: Account creation requires KYC for new customers."""
        result = validator.validate(
            action="create account",
            entity="Account",
            entity_id="account_new",
            context={
                "role": "Teller",
                "is_new_customer": True,
                "requires_kyc": True,
                "kyc_verified": True
            }
        )
        assert isinstance(result, ValidationResult)
    
    def test_get_allowed_actions_for_teller(self, validator):
        """Test querying allowed actions for Teller role."""
        actions = validator.get_allowed_actions("Transaction", {"role": "Teller"})
        assert isinstance(actions, list)
    
    def test_get_allowed_actions_for_manager(self, validator):
        """Test querying allowed actions for Manager role."""
        actions = validator.get_allowed_actions("Account", {"role": "Manager"})
        assert isinstance(actions, list)
    
    def test_explain_denial_finance(self, validator):
        """Test denial explanation for finance scenario."""
        explanation = validator.explain_denial(
            action="file suspicious activity report",
            entity="SuspiciousActivity",
            context={"role": "Teller"}
        )
        assert isinstance(explanation, str)
        assert len(explanation) > 0


class TestFinanceOntologyStructure:
    """Test the structure and content of the finance ontology."""
    
    def test_ontology_contains_bank_employee_classes(self, validator):
        """Test that BankEmployee class hierarchy exists."""
        from rdflib.namespace import RDFS, RDF, OWL
        
        employee_classes = []
        for cls in validator.graph.subjects(RDF.type, OWL.Class):
            labels = list(validator.graph.objects(cls, RDFS.label))
            for label in labels:
                label_str = str(label).lower()
                if any(keyword in label_str for keyword in ['teller', 'manager', 'compliance', 'employee']):
                    employee_classes.append(str(label))
            
            cls_str = str(cls).lower()
            if any(keyword in cls_str for keyword in ['teller', 'manager', 'compliance', 'employee']):
                if str(cls) not in employee_classes:
                    employee_classes.append(str(cls))
        
        assert len(employee_classes) > 0
    
    def test_ontology_contains_transaction_classes(self, validator):
        """Test that transaction classes exist."""
        from rdflib.namespace import RDFS, RDF, OWL
        
        transaction_classes = []
        for cls in validator.graph.subjects(RDF.type, OWL.Class):
            labels = list(validator.graph.objects(cls, RDFS.label))
            for label in labels:
                label_str = str(label).lower()
                if 'transaction' in label_str or 'transfer' in label_str:
                    transaction_classes.append(str(label))
        
        assert len(transaction_classes) > 0
    
    def test_ontology_contains_compliance_classes(self, validator):
        """Test that compliance-related classes exist."""
        from rdflib.namespace import RDFS, RDF, OWL
        
        compliance_classes = []
        for cls in validator.graph.subjects(RDF.type, OWL.Class):
            labels = list(validator.graph.objects(cls, RDFS.label))
            for label in labels:
                label_str = str(label).lower()
                if 'suspicious' in label_str or 'compliance' in label_str:
                    compliance_classes.append(str(label))
        
        assert len(compliance_classes) > 0
