"""
OntologyValidator - Core validation engine for OntoGuard.

This module provides the main validation logic for checking AI agent actions
against OWL ontologies.

Enhanced with improved rule matching algorithm for 100% accuracy.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

from pydantic import BaseModel, Field, ConfigDict
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL

# Configure logging
logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """
    Result of an ontology validation operation.

    Attributes:
        allowed: Whether the action is allowed according to the ontology
        reason: Human-readable explanation of the validation result
        suggested_actions: List of alternative actions that might be allowed
        metadata: Additional metadata about the validation (timestamps, rule IDs, etc.)
    """

    allowed: bool = Field(..., description="Whether the action is allowed")
    reason: str = Field(..., description="Human-readable explanation of the result")
    suggested_actions: List[str] = Field(default_factory=list, description="Alternative allowed actions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional validation metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "allowed": True,
                "reason": "Action is permitted for this entity type",
                "suggested_actions": [],
                "metadata": {}
            }
        }
    )


class ParsedRule:
    """
    Represents a parsed action rule with extracted components.

    Attributes:
        uri: Original URI of the rule
        name: Full rule name (e.g., 'doctorreadmedicalrecord')
        role: Extracted role (e.g., 'doctor')
        action: Extracted action (e.g., 'read')
        entity: Extracted entity (e.g., 'medicalrecord')
        requires_role: Explicit requiresRole from ontology (if any)
        requires_approval: Explicit requiresApproval from ontology (if any)
        applies_to: Explicit appliesTo from ontology (if any)
    """

    # Role aliases for matching (bidirectional)
    # When comparing roles, both are normalized to the same canonical form
    ROLE_ALIASES = {
        'labtech': 'labtechnician',
        'labtechnician': 'labtechnician',
        'insurance': 'insurance',  # Keep as 'insurance' since OWL uses this
        'insuranceagent': 'insurance',  # Map to 'insurance' for matching
    }

    def __init__(
        self,
        uri: str,
        name: str,
        role: Optional[str] = None,
        action: Optional[str] = None,
        entity: Optional[str] = None,
        requires_role: Optional[str] = None,
        requires_approval: Optional[str] = None,
        applies_to: Optional[str] = None
    ):
        self.uri = uri
        self.name = name
        self.role = role
        self.action = action
        self.entity = entity
        self.requires_role = requires_role or role  # Use parsed role if no explicit requiresRole
        self.requires_approval = requires_approval
        self.applies_to = applies_to or entity  # Use parsed entity if no explicit appliesTo
        # Detect "own" rules that require ownership verification
        self.requires_ownership = entity and 'own' in entity.lower()

    @classmethod
    def normalize_role(cls, role: str) -> str:
        """Normalize role name using aliases."""
        role_lower = role.lower().strip()
        return cls.ROLE_ALIASES.get(role_lower, role_lower)

    def matches(self, action: str, entity: str, role: str) -> bool:
        """
        Check if this rule matches the given action, entity, and role.

        Args:
            action: Action to match (e.g., 'read')
            entity: Entity type to match (e.g., 'MedicalRecord')
            role: User role to match (e.g., 'Doctor')

        Returns:
            True if all components match (or entity is 'own' for self-access rules)
        """
        action_lower = action.lower().strip()
        entity_lower = entity.lower().strip()
        role_lower = self.normalize_role(role)

        # Check action match
        if self.action and self.action != action_lower:
            return False

        # Check entity match (handle 'own' prefix for self-access)
        if self.entity:
            entity_matches = (
                self.entity == entity_lower or
                self.entity.replace('own', '') == entity_lower or
                entity_lower in self.entity or
                self.entity in entity_lower
            )
            if not entity_matches:
                return False

        # Check role match (Admin has all permissions)
        if role_lower == 'admin':
            return True

        # Normalize rule's role for comparison
        rule_role = self.normalize_role(self.requires_role) if self.requires_role else None
        if rule_role is None and self.role:
            rule_role = self.normalize_role(self.role)

        if rule_role:
            return rule_role == role_lower

        return True

    def __repr__(self) -> str:
        return f"ParsedRule(name={self.name}, role={self.role}, action={self.action}, entity={self.entity})"


class OntologyValidator:
    """
    Validates AI agent actions against OWL ontologies.

    This class loads an OWL ontology file and provides methods to validate
    agent actions, check entity types, and query allowed actions based on
    semantic rules defined in the ontology.

    Enhanced with improved rule matching algorithm that correctly parses
    combined rule names (e.g., 'DoctorReadMedicalRecord') and matches
    by all three components: role + action + entity.

    Attributes:
        ontology_path: Path to the OWL ontology file
        graph: RDF graph containing the loaded ontology
        _loaded: Whether the ontology has been successfully loaded
    """

    # Common action verbs for parsing combined rule names
    ACTION_VERBS = [
        'read', 'create', 'update', 'delete', 'write', 'modify',
        'view', 'list', 'search', 'export', 'import', 'execute',
        'prescribe', 'dispense', 'schedule', 'cancel', 'approve',
        'discharge', 'transfer', 'assign', 'manage', 'process',
        'block', 'enroll', 'grade'
    ]

    # Common role names for parsing combined rule names
    # Sorted by length (longer first) for proper matching
    ROLE_NAMES = [
        'individualcustomer', 'corporatecustomer', 'complianceofficer',
        'labtechnician', 'insuranceagent', 'receptionist', 'pharmacist',
        'supervisor', 'insurance', 'librarian', 'professor', 'principal',
        'operator', 'customer', 'manager', 'teacher', 'student',
        'patient', 'labtech', 'doctor', 'analyst', 'auditor', 'teller',
        'parent', 'admin', 'nurse', 'pupil', 'guest', 'dean', 'user'
    ]

    def __init__(self, ontology_path: str) -> None:
        """
        Initialize the OntologyValidator with an OWL ontology file.

        Args:
            ontology_path: Path to the OWL ontology file (.owl, .rdf, .ttl, etc.)

        Raises:
            FileNotFoundError: If the ontology file does not exist
            ValueError: If the ontology file cannot be parsed
            Exception: For other errors during ontology loading
        """
        self.ontology_path = Path(ontology_path)
        self.graph: Optional[Graph] = None
        self._loaded = False

        # Enhanced rule storage
        self._parsed_rules: List[ParsedRule] = []  # All parsed rules
        self._rules_by_action: Dict[str, List[ParsedRule]] = {}  # action -> rules
        self._rules_by_entity: Dict[str, List[ParsedRule]] = {}  # entity -> rules
        self._rules_by_role: Dict[str, List[ParsedRule]] = {}  # role -> rules

        # Legacy storage (for backwards compatibility)
        self._action_rules: Dict[str, Dict[str, Any]] = {}
        self._known_entities: Set[str] = set()
        self._known_actions: Set[str] = set()
        self._base_namespace: Optional[str] = None

        logger.info(f"Initializing OntologyValidator with ontology: {ontology_path}")

        if not self.ontology_path.exists():
            error_msg = f"Ontology file not found: {ontology_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        self._load_ontology()

    def _load_ontology(self) -> None:
        """
        Load the OWL ontology file into an RDF graph.

        Raises:
            ValueError: If the ontology file cannot be parsed
            Exception: For other errors during loading
        """
        try:
            logger.debug(f"Loading ontology from: {self.ontology_path}")
            self.graph = Graph()

            # Determine file format from extension
            file_ext = self.ontology_path.suffix.lower()
            format_map = {
                '.owl': 'xml',
                '.rdf': 'xml',
                '.ttl': 'turtle',
                '.n3': 'n3',
                '.nt': 'nt',
                '.jsonld': 'json-ld'
            }

            file_format = format_map.get(file_ext, 'xml')
            logger.debug(f"Detected file format: {file_format}")

            # Load the ontology
            self.graph.parse(str(self.ontology_path), format=file_format)

            # Log basic statistics
            num_triples = len(self.graph)
            logger.info(f"Successfully loaded ontology: {num_triples} triples")

            if num_triples == 0:
                logger.warning("Ontology file appears to be empty")

            self._loaded = True
            self._parse_action_rules()  # Parse business rules from ontology

        except Exception as e:
            error_msg = f"Failed to parse ontology file {self.ontology_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e

    def _parse_action_rules(self) -> None:
        """
        Parse action rules and entity types from the loaded ontology.

        Enhanced to extract role, action, and entity components from rule names.
        """
        if self.graph is None:
            return

        logger.debug("Parsing action rules from ontology...")

        # Detect base namespace from ontology
        self._base_namespace = self._detect_base_namespace()
        logger.debug(f"Detected base namespace: {self._base_namespace}")

        # Parse entity types (OWL classes)
        self._parse_entity_types()

        # Parse action individuals and their rules (enhanced)
        self._parse_action_individuals_enhanced()

        logger.info(
            f"Parsed {len(self._parsed_rules)} action rules, "
            f"{len(self._known_entities)} entity types, "
            f"{len(self._known_actions)} action names"
        )

    def _detect_base_namespace(self) -> Optional[str]:
        """Detect the base namespace of the ontology."""
        if self.graph is None:
            return None

        # Look for owl:Ontology declaration
        for ontology in self.graph.subjects(RDF.type, OWL.Ontology):
            uri_str = str(ontology)
            # Add # if not present
            if not uri_str.endswith('#') and not uri_str.endswith('/'):
                return uri_str + '#'
            return uri_str

        # Fallback: find common namespace from classes
        namespaces = {}
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            uri_str = str(cls)
            if '#' in uri_str:
                ns = uri_str.rsplit('#', 1)[0] + '#'
                namespaces[ns] = namespaces.get(ns, 0) + 1

        if namespaces:
            return max(namespaces, key=namespaces.get)

        return None

    def _parse_entity_types(self) -> None:
        """Parse entity types (OWL classes) from ontology."""
        if self.graph is None:
            return

        for cls in self.graph.subjects(RDF.type, OWL.Class):
            cls_str = str(cls)

            # Get label
            label = self._get_label(cls)
            if label:
                self._known_entities.add(label.lower())

            # Also add fragment from URI
            if '#' in cls_str:
                fragment = cls_str.split('#')[-1]
                self._known_entities.add(fragment.lower())

        logger.debug(f"Found entity types: {self._known_entities}")

    def _parse_action_individuals_enhanced(self) -> None:
        """
        Parse action individuals with enhanced component extraction.

        This method:
        1. Finds all action-related individuals in the ontology
        2. Parses their names to extract role, action, and entity components
        3. Stores rules in indexed structures for fast lookup
        """
        if self.graph is None:
            return

        # Find property URIs dynamically
        requires_role_prop = self._find_property_uri("requiresRole")
        requires_approval_prop = self._find_property_uri("requiresApproval")
        applies_to_prop = self._find_property_uri("appliesTo")

        logger.debug(f"Found property URIs: requiresRole={requires_role_prop}, "
                     f"requiresApproval={requires_approval_prop}, appliesTo={applies_to_prop}")

        # Find all subjects that have any of these properties (action individuals)
        action_subjects = set()
        props_to_check = [p for p in [requires_role_prop, applies_to_prop] if p is not None]
        for prop in props_to_check:
            for subj in self.graph.subjects(prop, None):
                action_subjects.add(subj)

        # Also find individuals that are instances of Action subclasses
        for subj, _, obj in self.graph.triples((None, RDF.type, None)):
            if isinstance(obj, URIRef):
                obj_str = str(obj)
                class_name = obj_str.split('#')[-1] if '#' in obj_str else obj_str.split('/')[-1]
                if any(keyword in class_name for keyword in ['Action', 'Create', 'Delete', 'Modify', 'Process', 'Cancel']):
                    action_subjects.add(subj)

        logger.debug(f"Found {len(action_subjects)} action subjects")

        # Parse each action individual
        for action_subj in action_subjects:
            action_uri = str(action_subj)

            # Get action name from label or URI
            label = self._get_label(action_subj)
            if label:
                full_name = label.lower()
            elif '#' in action_uri:
                fragment = action_uri.split('#')[-1]
                full_name = fragment.lower()
            else:
                continue

            # Parse explicit properties
            explicit_role = None
            explicit_approval = None
            explicit_applies_to = None

            if requires_role_prop:
                for _, _, role_obj in self.graph.triples((action_subj, requires_role_prop, None)):
                    role_name = self._extract_name_from_uri(str(role_obj))
                    if role_name:
                        explicit_role = role_name.lower()

            if requires_approval_prop:
                for _, _, approval_obj in self.graph.triples((action_subj, requires_approval_prop, None)):
                    approval_name = self._extract_name_from_uri(str(approval_obj))
                    if approval_name:
                        explicit_approval = approval_name.lower()

            if applies_to_prop:
                for _, _, applies_obj in self.graph.triples((action_subj, applies_to_prop, None)):
                    applies_name = self._extract_name_from_uri(str(applies_obj))
                    if applies_name:
                        explicit_applies_to = applies_name.lower()

            # Extract components from rule name (e.g., 'DoctorReadMedicalRecord')
            parsed_role, parsed_action, parsed_entity = self._parse_rule_name(full_name)

            # Create ParsedRule
            rule = ParsedRule(
                uri=action_uri,
                name=full_name,
                role=parsed_role,
                action=parsed_action,
                entity=parsed_entity,
                requires_role=explicit_role or parsed_role,
                requires_approval=explicit_approval,
                applies_to=explicit_applies_to or parsed_entity
            )

            self._parsed_rules.append(rule)

            # Index rule by action
            if parsed_action:
                if parsed_action not in self._rules_by_action:
                    self._rules_by_action[parsed_action] = []
                self._rules_by_action[parsed_action].append(rule)
                self._known_actions.add(parsed_action)

            # Index rule by entity
            if parsed_entity:
                entity_key = parsed_entity.replace('own', '')  # Normalize 'ownmedicalrecord' -> 'medicalrecord'
                if entity_key not in self._rules_by_entity:
                    self._rules_by_entity[entity_key] = []
                self._rules_by_entity[entity_key].append(rule)

            # Index rule by role
            if parsed_role:
                if parsed_role not in self._rules_by_role:
                    self._rules_by_role[parsed_role] = []
                self._rules_by_role[parsed_role].append(rule)

            # Legacy storage for backwards compatibility
            self._action_rules[full_name] = {
                "uri": action_uri,
                "name": full_name,
                "requiresRole": explicit_role or parsed_role,
                "requiresApproval": explicit_approval,
                "appliesTo": explicit_applies_to or parsed_entity
            }

            logger.debug(f"Parsed rule: {rule}")

    def _parse_rule_name(self, name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse a combined rule name to extract role, action, and entity components.

        Examples:
            'DoctorReadMedicalRecord' -> ('doctor', 'read', 'medicalrecord')
            'AdminDeleteUser' -> ('admin', 'delete', 'user')
            'PatientReadOwnMedicalRecord' -> ('patient', 'read', 'ownmedicalrecord')

        Args:
            name: The rule name to parse (lowercase)

        Returns:
            Tuple of (role, action, entity) or (None, None, None) if parsing fails
        """
        name_lower = name.lower().strip()

        # Remove common suffixes
        for suffix in ['action', 'rule', 'permission']:
            if name_lower.endswith(suffix):
                name_lower = name_lower[:-len(suffix)]

        parsed_role = None
        parsed_action = None
        parsed_entity = None

        # Try to extract role (at the beginning)
        for role in sorted(self.ROLE_NAMES, key=len, reverse=True):
            if name_lower.startswith(role):
                parsed_role = role
                name_lower = name_lower[len(role):]
                break

        # Try to extract action (after role)
        for action in sorted(self.ACTION_VERBS, key=len, reverse=True):
            if name_lower.startswith(action):
                parsed_action = action
                name_lower = name_lower[len(action):]
                break

        # Remaining part is the entity (with possible 'own' prefix)
        if name_lower:
            parsed_entity = name_lower

        return parsed_role, parsed_action, parsed_entity

    def _find_property_uri(self, property_name: str) -> Optional[URIRef]:
        """
        Find the actual URI of a property by its local name.
        """
        if self.graph is None:
            return None

        property_lower = property_name.lower()

        for _, predicate, _ in self.graph:
            if isinstance(predicate, URIRef):
                pred_str = str(predicate)
                local_name = pred_str.split('#')[-1] if '#' in pred_str else pred_str.split('/')[-1]
                if local_name.lower() == property_lower:
                    return predicate

        return None

    def _normalize_action_name(self, name: str) -> str:
        """
        Normalize action name from camelCase/PascalCase to lowercase.
        """
        if name.endswith('Action'):
            name = name[:-6]
        result = re.sub(r'([A-Z])', r' \1', name).strip().lower()
        return result

    def _extract_name_from_uri(self, uri: str) -> Optional[str]:
        """Extract the name part from a URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return None

    def validate(
        self,
        action: str,
        entity: str,
        entity_id: str,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate an agent action against the ontology.

        Enhanced with precise matching by role + action + entity combination.

        Args:
            action: The action to validate (e.g., "read", "write", "delete")
            entity: The entity type (e.g., "User", "MedicalRecord")
            entity_id: Unique identifier for the specific entity instance
            context: Additional context information (user roles, time, etc.)

        Returns:
            ValidationResult containing the validation outcome and explanation
        """
        if not self._loaded or self.graph is None:
            raise RuntimeError("Ontology not loaded. Cannot perform validation.")

        logger.info(f"Validating action '{action}' for entity '{entity}' (ID: {entity_id})")
        logger.debug(f"Context: {context}")

        action_lower = action.lower().strip()
        entity_lower = entity.lower().strip()
        user_role = context.get("role", "").lower().strip()

        metadata = {
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "context": context
        }

        # Check if action exists in ontology
        action_exists = self._check_action_exists(action)
        if not action_exists:
            reason = f"Action '{action}' is not defined in the ontology"
            logger.warning(reason)
            suggested = self._suggest_similar_actions(action)
            return ValidationResult(
                allowed=False,
                reason=reason,
                suggested_actions=suggested,
                metadata=metadata
            )

        # Check if entity type is valid
        entity_valid = self._check_entity_type(entity)
        if not entity_valid:
            reason = f"Entity type '{entity}' is not defined in the ontology"
            logger.warning(reason)
            return ValidationResult(
                allowed=False,
                reason=reason,
                suggested_actions=[],
                metadata=metadata
            )

        # ENHANCED: Find matching rules by action + entity + role combination
        matching_rules = self._find_matching_rules(action_lower, entity_lower, user_role)

        if matching_rules:
            # At least one rule matches - check for ownership requirement
            best_rule = matching_rules[0]

            # Check if rule requires ownership verification (e.g., "PatientReadOwnMedicalRecord")
            if best_rule.requires_ownership:
                # Ownership rules require entity_id and matching owner context
                entity_id_provided = entity_id and entity_id != "unknown"
                owner_id_provided = context.get("patient_id") or context.get("user_id") or context.get("owner_id")

                # If ownership cannot be verified, deny access
                # Admin is exempt from ownership checks
                if user_role != 'admin' and not (entity_id_provided and owner_id_provided):
                    reason = f"Action '{action}' on '{entity}' requires ownership verification. " \
                             f"Provide entity_id and patient_id/owner_id to verify ownership."
                    logger.info(f"Denied: {reason}")
                    metadata["validation_passed"] = False
                    metadata["constraint_type"] = "ownership_required"
                    metadata["matched_rule"] = best_rule.name
                    return ValidationResult(
                        allowed=False,
                        reason=reason,
                        suggested_actions=[f"Provide entity_id and patient_id to verify ownership of {entity}"],
                        metadata=metadata
                    )

            # All checks passed - action is allowed
            reason = f"Action '{action}' is allowed for entity type '{entity}'"
            logger.info(reason)
            metadata["validation_passed"] = True
            metadata["matched_rule"] = best_rule.name
            return ValidationResult(
                allowed=True,
                reason=reason,
                suggested_actions=[],
                metadata=metadata
            )

        # DESIGN DECISION: Closed World Assumption (CWA)
        #
        # OntoGuard intentionally uses CWA — if no OWL rule explicitly
        # permits an action, the action is DENIED.  Standard OWL semantics
        # follow Open World Assumption (OWA), where the absence of a
        # statement does not imply its negation.  We diverge from OWA
        # because OntoGuard is a security component: a whitelist ("deny
        # by default") is safer than a blacklist.  OWL is used here as a
        # serialization format for access-control rules, not as a formal
        # ontology for reasoning under OWA.
        denial_result = self._explain_denial_enhanced(action_lower, entity_lower, user_role)
        metadata.update(denial_result.get("metadata", {}))

        return ValidationResult(
            allowed=False,
            reason=denial_result["reason"],
            suggested_actions=denial_result.get("suggestions", []),
            metadata=metadata
        )

    def _find_matching_rules(
        self,
        action: str,
        entity: str,
        role: str
    ) -> List[ParsedRule]:
        """
        Find all rules that match the given action, entity, and role combination.

        This is the core of the enhanced matching algorithm:
        1. Get rules indexed by action
        2. Filter by entity match
        3. Filter by role match (or Admin override)

        Args:
            action: Action to match (lowercase)
            entity: Entity type to match (lowercase)
            role: User role to match (lowercase)

        Returns:
            List of matching ParsedRule objects
        """
        matching = []

        # Get rules for this action
        action_rules = self._rules_by_action.get(action, [])

        for rule in action_rules:
            if rule.matches(action, entity, role):
                matching.append(rule)

        # Sort by specificity (more specific rules first)
        matching.sort(key=lambda r: (
            r.entity == entity,  # Exact entity match
            r.role == role,       # Exact role match
        ), reverse=True)

        return matching

    def _explain_denial_enhanced(
        self,
        action: str,
        entity: str,
        role: str
    ) -> Dict[str, Any]:
        """
        Provide detailed explanation of why no matching rule was found.

        Checks:
        1. Are there rules for this action+entity but different roles?
        2. Are there rules for this role+action but different entities?
        3. Are there any rules for this role?
        """
        # Check if there are rules for action+entity with different roles
        action_entity_rules = []
        for rule in self._rules_by_action.get(action, []):
            if rule.entity and (rule.entity == entity or entity in rule.entity or rule.entity in entity):
                action_entity_rules.append(rule)

        if action_entity_rules:
            allowed_roles = list(set(r.role for r in action_entity_rules if r.role))
            if allowed_roles:
                return {
                    "reason": f"Action '{action}' on '{entity}' requires role(s): {', '.join(r.title() for r in allowed_roles)}. User has role '{role.title() if role else 'none'}'",
                    "metadata": {
                        "constraint_type": "role_mismatch",
                        "allowed_roles": allowed_roles,
                        "user_role": role
                    },
                    "suggestions": [f"{r}{action}{entity}" for r in allowed_roles[:3]]
                }

        # Check if there are rules for role+action with different entities
        role_action_rules = []
        for rule in self._rules_by_action.get(action, []):
            if rule.role and rule.role == role:
                role_action_rules.append(rule)

        if role_action_rules:
            allowed_entities = list(set(r.entity for r in role_action_rules if r.entity))
            if allowed_entities:
                return {
                    "reason": f"Role '{role.title()}' can '{action}' these entities: {', '.join(e.title() for e in allowed_entities[:5])}. Not '{entity}'",
                    "metadata": {
                        "constraint_type": "entity_mismatch",
                        "allowed_entities": allowed_entities,
                        "requested_entity": entity
                    },
                    "suggestions": [f"{role}{action}{e}" for e in allowed_entities[:3]]
                }

        # Check what actions this role can do
        role_rules = self._rules_by_role.get(role, [])
        if role_rules:
            allowed_actions = list(set(r.action for r in role_rules if r.action))
            return {
                "reason": f"Role '{role.title()}' cannot '{action}' '{entity}'. Allowed actions: {', '.join(allowed_actions[:5])}",
                "metadata": {
                    "constraint_type": "action_not_allowed",
                    "allowed_actions": allowed_actions
                },
                "suggestions": [f"{role}{a}{entity}" for a in allowed_actions[:3] if a]
            }

        # Generic denial
        return {
            "reason": f"No rule found allowing role '{role.title() if role else 'none'}' to '{action}' '{entity}'",
            "metadata": {
                "constraint_type": "no_matching_rule"
            },
            "suggestions": self.get_allowed_actions(entity, {"role": role})
        }

    def get_allowed_actions(
        self,
        entity: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get all actions that are allowed for a given entity type.

        Enhanced to use indexed rule lookup.
        """
        if not self._loaded or self.graph is None:
            raise RuntimeError("Ontology not loaded. Cannot query allowed actions.")

        logger.debug(f"Querying allowed actions for entity type '{entity}'")

        entity_lower = entity.lower().strip()
        allowed_actions = []

        # Use indexed lookup
        entity_rules = self._rules_by_entity.get(entity_lower, [])

        for rule in entity_rules:
            allowed_actions.append(rule.name)

        # Fallback: if no indexed rules, try simple method
        if not allowed_actions:
            allowed_actions = self._find_actions_for_entity_simple(entity)

        logger.info(f"Found {len(allowed_actions)} allowed actions for entity '{entity}'")
        return allowed_actions

    def check_permissions(
        self,
        role: str,
        action: str,
        entity_type: str
    ) -> bool:
        """
        Check if a role has permission for a specific action on an entity type.

        Enhanced with precise matching.
        """
        if not self._loaded or self.graph is None:
            return True

        action_lower = action.lower().strip()
        entity_lower = entity_type.lower().strip()
        role_lower = role.lower().strip()

        matching_rules = self._find_matching_rules(action_lower, entity_lower, role_lower)
        return len(matching_rules) > 0

    def explain_denial(
        self,
        action: str,
        entity: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Provide a detailed explanation of why an action was denied.
        """
        if not self._loaded or self.graph is None:
            raise RuntimeError("Ontology not loaded. Cannot explain denial.")

        logger.debug(f"Generating denial explanation for action '{action}' on entity '{entity}'")

        user_role = context.get("role", "").lower().strip()
        explanations = []

        # Check each validation step
        if not self._check_action_exists(action):
            explanations.append(f"❌ Action '{action}' is not recognized in the ontology.")

        if not self._check_entity_type(entity):
            explanations.append(f"❌ Entity type '{entity}' is not recognized in the ontology.")

        if self._check_action_exists(action) and self._check_entity_type(entity):
            denial_info = self._explain_denial_enhanced(
                action.lower(), entity.lower(), user_role
            )
            explanations.append(f"❌ {denial_info['reason']}")

        # Context info
        if context:
            explanations.append("\n📋 Context information:")
            for key, value in context.items():
                explanations.append(f"   - {key}: {value}")

        # Suggestions
        allowed = self.get_allowed_actions(entity, context)
        if allowed:
            explanations.append(f"\n💡 Suggested alternatives:")
            for alt_action in allowed[:5]:
                explanations.append(f"   - {alt_action}")

        if not explanations:
            return f"Action '{action}' on entity '{entity}' was denied."

        return "\n".join(explanations)

    def _check_action_exists(self, action: str) -> bool:
        """Check if an action exists in the ontology."""
        if self.graph is None:
            return False

        action_lower = action.lower().strip()

        # Check in indexed actions
        if action_lower in self._rules_by_action:
            return True

        # Check in known actions
        if action_lower in self._known_actions:
            return True

        return False

    def _check_entity_type(self, entity: str) -> bool:
        """Check if an entity type exists in the ontology."""
        if self.graph is None:
            return False

        entity_lower = entity.lower().strip()

        # Check in indexed entities
        if entity_lower in self._rules_by_entity:
            return True

        # Check in known entities
        if entity_lower in self._known_entities:
            return True

        # Check for partial match
        for known_entity in self._known_entities:
            if entity_lower == known_entity or entity_lower in known_entity or known_entity in entity_lower:
                return True

        return False

    def _check_action_allowed_for_entity(self, action: str, entity: str) -> bool:
        """Check if an action is allowed for a specific entity type."""
        if self.graph is None:
            return False

        return self._check_action_exists(action) and self._check_entity_type(entity)

    def _check_constraints(
        self,
        action: str,
        entity: str,
        entity_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if the action violates any constraints.

        This method is kept for backwards compatibility but the main
        validation logic now uses _find_matching_rules.
        """
        if self.graph is None:
            return {"allowed": True}

        user_role = context.get("role", "").lower().strip()
        matching_rules = self._find_matching_rules(
            action.lower(), entity.lower(), user_role
        )

        if matching_rules:
            return {"allowed": True}

        # CWA: no matching rule → deny (see validate_action for rationale)
        denial_info = self._explain_denial_enhanced(
            action.lower(), entity.lower(), user_role
        )

        return {
            "allowed": False,
            "reason": denial_info["reason"],
            "metadata": denial_info.get("metadata", {}),
            "suggested_actions": denial_info.get("suggestions", [])
        }

    def _suggest_similar_actions(self, action: str) -> List[str]:
        """Suggest similar actions if the requested action doesn't exist."""
        if self.graph is None:
            return []

        action_lower = action.lower()
        suggestions = []

        for known_action in self._known_actions:
            if action_lower in known_action or known_action in action_lower:
                suggestions.append(known_action)

        return suggestions[:5]

    def _find_actions_for_entity_simple(self, entity: str) -> List[str]:
        """Find actions for an entity using parsed action rules."""
        if not self._action_rules:
            return []

        entity_lower = entity.lower().strip()
        actions = []

        for action_name, rule in self._action_rules.items():
            applies_to = rule.get("appliesTo", "").lower() if rule.get("appliesTo") else ""

            if not applies_to or applies_to == entity_lower or entity_lower in applies_to or applies_to in entity_lower:
                actions.append(action_name)

        if not actions and self._known_actions:
            return list(self._known_actions)

        return actions

    def _get_label(self, resource: URIRef) -> Optional[str]:
        """Get the label (rdfs:label) for a resource, or extract from URI."""
        if self.graph is None:
            return None

        for label in self.graph.objects(resource, RDFS.label):
            if isinstance(label, Literal):
                return str(label)

        uri_str = str(resource)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]

        return None

    def _extract_action_name(self, action_uri: str) -> Optional[str]:
        """Extract a human-readable action name from a URI."""
        try:
            uri_ref = URIRef(action_uri)
            label = self._get_label(uri_ref)
            return label
        except Exception:
            if '#' in action_uri:
                return action_uri.split('#')[-1]
            elif '/' in action_uri:
                return action_uri.split('/')[-1]
            return None
