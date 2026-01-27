"""
OntologyValidator - Core validation engine for OntoGuard.

This module provides the main validation logic for checking AI agent actions
against OWL ontologies.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

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


class OntologyValidator:
    """
    Validates AI agent actions against OWL ontologies.
    
    This class loads an OWL ontology file and provides methods to validate
    agent actions, check entity types, and query allowed actions based on
    semantic rules defined in the ontology.
    
    Attributes:
        ontology_path: Path to the OWL ontology file
        graph: RDF graph containing the loaded ontology
        _loaded: Whether the ontology has been successfully loaded
    """
    
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

        # Parsed business rules from ontology
        self._action_rules: Dict[str, Dict[str, Any]] = {}  # action_name -> {requiresRole, appliesTo, etc.}
        self._known_entities: Set[str] = set()  # Known entity types from ontology
        self._known_actions: Set[str] = set()  # Known action names from ontology
        self._base_namespace: Optional[str] = None  # Ontology base namespace
        
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

        This method extracts:
        - Action individuals with their requiresRole, requiresApproval, appliesTo properties
        - Known entity types (OWL classes)
        - Known action names

        The extracted rules are stored in _action_rules, _known_entities, _known_actions.
        """
        if self.graph is None:
            return

        logger.debug("Parsing action rules from ontology...")

        # Detect base namespace from ontology
        self._base_namespace = self._detect_base_namespace()
        logger.debug(f"Detected base namespace: {self._base_namespace}")

        # Parse entity types (OWL classes)
        self._parse_entity_types()

        # Parse action individuals and their rules
        self._parse_action_individuals()

        logger.info(
            f"Parsed {len(self._action_rules)} action rules, "
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

    def _parse_action_individuals(self) -> None:
        """Parse action individuals and their rules from ontology."""
        if self.graph is None:
            return

        # Find property URIs dynamically by scanning the graph
        requires_role_prop = self._find_property_uri("requiresRole")
        requires_approval_prop = self._find_property_uri("requiresApproval")
        applies_to_prop = self._find_property_uri("appliesTo")

        logger.debug(f"Found property URIs: requiresRole={requires_role_prop}, "
                     f"requiresApproval={requires_approval_prop}, appliesTo={applies_to_prop}")

        # Find all subjects that have any of these properties (they are action individuals)
        action_subjects = set()
        props_to_check = [p for p in [requires_role_prop, applies_to_prop] if p is not None]
        for prop in props_to_check:
            for subj in self.graph.subjects(prop, None):
                action_subjects.add(subj)

        # Also find individuals that are instances of Action subclasses
        for subj, _, obj in self.graph.triples((None, RDF.type, None)):
            # Check if obj is a subclass of Action
            if isinstance(obj, URIRef):
                obj_str = str(obj)
                # Extract class name from URI
                class_name = obj_str.split('#')[-1] if '#' in obj_str else obj_str.split('/')[-1]
                # Common action class names
                if any(keyword in class_name for keyword in ['Action', 'Create', 'Delete', 'Modify', 'Process', 'Cancel']):
                    action_subjects.add(subj)

        logger.debug(f"Found {len(action_subjects)} action subjects")

        # Parse each action individual
        for action_subj in action_subjects:
            action_uri = str(action_subj)

            # Get action name from label or URI
            label = self._get_label(action_subj)
            if label:
                action_name = label.lower()
            elif '#' in action_uri:
                # Extract from URI and convert camelCase to spaces
                fragment = action_uri.split('#')[-1]
                action_name = self._normalize_action_name(fragment)
            else:
                continue

            # Parse rule properties
            rule: Dict[str, Any] = {
                "uri": action_uri,
                "name": action_name,
            }

            # Get requiresRole
            if requires_role_prop:
                for _, _, role_obj in self.graph.triples((action_subj, requires_role_prop, None)):
                    role_name = self._extract_name_from_uri(str(role_obj))
                    if role_name:
                        rule["requiresRole"] = role_name.lower()

            # Get requiresApproval
            if requires_approval_prop:
                for _, _, approval_obj in self.graph.triples((action_subj, requires_approval_prop, None)):
                    approval_name = self._extract_name_from_uri(str(approval_obj))
                    if approval_name:
                        rule["requiresApproval"] = approval_name.lower()

            # Get appliesTo
            if applies_to_prop:
                for _, _, applies_obj in self.graph.triples((action_subj, applies_to_prop, None)):
                    applies_name = self._extract_name_from_uri(str(applies_obj))
                    if applies_name:
                        rule["appliesTo"] = applies_name.lower()

            # Store rule
            self._action_rules[action_name] = rule
            self._known_actions.add(action_name)

            logger.debug(f"Parsed action rule: {action_name} -> {rule}")

    def _find_property_uri(self, property_name: str) -> Optional[URIRef]:
        """
        Find the actual URI of a property by its local name.

        This handles cases where the property namespace differs from the ontology namespace.
        """
        if self.graph is None:
            return None

        property_lower = property_name.lower()

        # Scan all predicates in the graph
        for _, predicate, _ in self.graph:
            if isinstance(predicate, URIRef):
                pred_str = str(predicate)
                # Extract local name
                local_name = pred_str.split('#')[-1] if '#' in pred_str else pred_str.split('/')[-1]
                if local_name.lower() == property_lower:
                    return predicate

        return None

    def _normalize_action_name(self, name: str) -> str:
        """
        Normalize action name from camelCase/PascalCase to space-separated lowercase.

        Example: deleteUserAction -> delete user
        """
        import re
        # Remove 'Action' suffix
        if name.endswith('Action'):
            name = name[:-6]
        # Insert space before uppercase letters and lowercase everything
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
        
        This method checks:
        1. If the action exists in the ontology
        2. If the entity type is valid
        3. If there are any constraints (permissions, temporal rules, etc.)
        
        Args:
            action: The action to validate (e.g., "read", "write", "delete")
            entity: The entity type (e.g., "User", "Document", "Resource")
            entity_id: Unique identifier for the specific entity instance
            context: Additional context information (user roles, time, etc.)
            
        Returns:
            ValidationResult containing the validation outcome and explanation
            
        Raises:
            RuntimeError: If the ontology has not been loaded successfully
        """
        if not self._loaded or self.graph is None:
            raise RuntimeError("Ontology not loaded. Cannot perform validation.")
        
        logger.info(f"Validating action '{action}' for entity '{entity}' (ID: {entity_id})")
        logger.debug(f"Context: {context}")
        
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
        
        # Check if action is allowed for this entity type
        action_allowed = self._check_action_allowed_for_entity(action, entity)
        if not action_allowed:
            reason = f"Action '{action}' is not permitted for entity type '{entity}'"
            logger.warning(reason)
            suggested = self.get_allowed_actions(entity, context)
            return ValidationResult(
                allowed=False,
                reason=reason,
                suggested_actions=suggested,
                metadata=metadata
            )
        
        # Check constraints (permissions, temporal rules, etc.)
        constraint_check = self._check_constraints(action, entity, entity_id, context)
        if not constraint_check["allowed"]:
            reason = constraint_check.get("reason", "Action violates ontology constraints")
            logger.warning(reason)
            suggested = constraint_check.get("suggested_actions", [])
            metadata.update(constraint_check.get("metadata", {}))
            return ValidationResult(
                allowed=False,
                reason=reason,
                suggested_actions=suggested,
                metadata=metadata
            )
        
        # All checks passed
        reason = f"Action '{action}' is allowed for entity type '{entity}'"
        logger.info(reason)
        metadata["validation_passed"] = True
        return ValidationResult(
            allowed=True,
            reason=reason,
            suggested_actions=[],
            metadata=metadata
        )
    
    def get_allowed_actions(
        self,
        entity: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get all actions that are allowed for a given entity type.
        
        Args:
            entity: The entity type to query
            context: Additional context information (user roles, time, etc.)
            
        Returns:
            List of allowed action names
            
        Raises:
            RuntimeError: If the ontology has not been loaded successfully
        """
        if not self._loaded or self.graph is None:
            raise RuntimeError("Ontology not loaded. Cannot query allowed actions.")
        
        logger.debug(f"Querying allowed actions for entity type '{entity}'")
        
        allowed_actions = []
        
        # Query for actions associated with this entity type
        # This is a simplified query - in a real implementation, you'd have
        # more sophisticated SPARQL queries based on your ontology structure
        try:
            # Look for actions that are permitted for this entity
            # This assumes your ontology has properties like "hasAction" or "allowsAction"
            query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            
            SELECT DISTINCT ?action
            WHERE {{
                ?entity rdf:type ?entityType .
                ?entityType rdfs:label ?entityLabel .
                FILTER(LCASE(?entityLabel) = LCASE("{entity}"))
                ?entityType ?property ?action .
                ?action rdf:type ?actionType .
                FILTER(?property IN (owl:hasAction, rdfs:seeAlso, <http://example.org/ontoguard/allowsAction>))
            }}
            """
            
            results = self.graph.query(query)
            for row in results:
                action_uri = str(row.action)
                # Extract action name from URI or use label
                action_name = self._extract_action_name(action_uri)
                if action_name:
                    allowed_actions.append(action_name)
            
            # Fallback: if SPARQL doesn't work, try simpler graph traversal
            if not allowed_actions:
                allowed_actions = self._find_actions_for_entity_simple(entity)
            
        except Exception as e:
            logger.warning(f"Error querying allowed actions: {e}. Using fallback method.")
            allowed_actions = self._find_actions_for_entity_simple(entity)
        
        logger.info(f"Found {len(allowed_actions)} allowed actions for entity '{entity}'")
        return allowed_actions
    
    def explain_denial(
        self,
        action: str,
        entity: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Provide a detailed explanation of why an action was denied.
        
        Args:
            action: The action that was denied
            entity: The entity type involved
            context: Additional context information
            
        Returns:
            Human-readable explanation of the denial
            
        Raises:
            RuntimeError: If the ontology has not been loaded successfully
        """
        if not self._loaded or self.graph is None:
            raise RuntimeError("Ontology not loaded. Cannot explain denial.")
        
        logger.debug(f"Generating denial explanation for action '{action}' on entity '{entity}'")
        
        explanations = []
        
        # Check each validation step and explain failures
        if not self._check_action_exists(action):
            explanations.append(f"❌ Action '{action}' is not recognized in the ontology.")
            explanations.append("   This action may not be defined or may be misspelled.")
        
        if not self._check_entity_type(entity):
            explanations.append(f"❌ Entity type '{entity}' is not recognized in the ontology.")
            explanations.append("   Please verify the entity type name.")
        
        if self._check_action_exists(action) and self._check_entity_type(entity):
            if not self._check_action_allowed_for_entity(action, entity):
                explanations.append(f"❌ Action '{action}' is not permitted for entity type '{entity}'.")
                explanations.append("   This action may only be allowed for other entity types.")
            
            constraint_check = self._check_constraints(action, entity, "", context)
            if not constraint_check["allowed"]:
                explanations.append(f"❌ Action '{action}' violates ontology constraints.")
                explanations.append(f"   {constraint_check.get('reason', 'Constraint violation detected.')}")
        
        # Add context information
        if context:
            explanations.append("\n📋 Context information:")
            for key, value in context.items():
                explanations.append(f"   - {key}: {value}")
        
        # Suggest alternatives
        allowed = self.get_allowed_actions(entity, context)
        if allowed:
            explanations.append(f"\n💡 Suggested alternatives:")
            for alt_action in allowed[:5]:  # Limit to 5 suggestions
                explanations.append(f"   - {alt_action}")
        
        if not explanations:
            return f"Action '{action}' on entity '{entity}' was denied, but no specific reason could be determined."
        
        return "\n".join(explanations)
    
    def _check_action_exists(self, action: str) -> bool:
        """Check if an action exists in the ontology using parsed rules."""
        if self.graph is None:
            return False

        action_lower = action.lower().strip()

        # First, check in parsed action rules (most reliable)
        if action_lower in self._known_actions:
            return True

        # Check for partial matches (e.g., "delete user" matches "delete user")
        for known_action in self._known_actions:
            if action_lower == known_action or action_lower in known_action or known_action in action_lower:
                return True

        # If we have parsed rules but action not found, return False
        if self._known_actions:
            return False

        # Fallback for ontologies without parsed rules: check in graph
        for subject, _, obj in self.graph:
            if isinstance(subject, URIRef):
                label = self._get_label(subject)
                if label and action_lower in label.lower():
                    return True
            if isinstance(obj, (URIRef, Literal)):
                label = self._get_label(obj) if isinstance(obj, URIRef) else str(obj)
                if label and action_lower in label.lower():
                    return True

        return False  # Action not found in ontology
    
    def _check_entity_type(self, entity: str) -> bool:
        """Check if an entity type exists in the ontology using parsed entities."""
        if self.graph is None:
            return False

        entity_lower = entity.lower().strip()

        # First, check in parsed known entities (most reliable)
        if entity_lower in self._known_entities:
            return True

        # Check for partial matches
        for known_entity in self._known_entities:
            if entity_lower == known_entity or entity_lower in known_entity or known_entity in entity_lower:
                return True

        # If we have parsed entities but entity not found, return False
        if self._known_entities:
            return False

        # Fallback for ontologies without parsed entities: check in graph
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            if isinstance(cls, URIRef):
                label = self._get_label(cls)
                if label and entity_lower in label.lower():
                    return True

        return False  # Entity type not found in ontology
    
    def _check_action_allowed_for_entity(self, action: str, entity: str) -> bool:
        """Check if an action is allowed for a specific entity type."""
        if self.graph is None:
            return False
        
        # This is a simplified check - in a real implementation, you'd query
        # the ontology for specific permission rules
        # For now, we'll assume actions are allowed if both exist
        return self._check_action_exists(action) and self._check_entity_type(entity)
    
    def _check_constraints(
        self,
        action: str,
        entity: str,
        entity_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if the action violates any constraints (permissions, temporal rules, etc.).

        This method checks:
        1. requiresRole from OWL ontology rules
        2. requiresApproval from OWL ontology rules
        3. appliesTo entity type matching
        4. Legacy: required_role from context (backwards compatibility)

        Returns:
            Dictionary with 'allowed' key and optional 'reason' and 'metadata' keys
        """
        if self.graph is None:
            return {"allowed": True}

        action_lower = action.lower().strip()
        entity_lower = entity.lower().strip()
        user_role = context.get("role", "").lower().strip()

        # Find the action rule (try exact match first, then partial)
        rule = self._find_action_rule(action_lower)

        if rule:
            # Check 1: requiresRole from OWL
            if "requiresRole" in rule:
                required_role = rule["requiresRole"].lower()

                # Admin has all permissions (hierarchy)
                if user_role == "admin":
                    pass  # Admin can do anything
                elif user_role != required_role:
                    return {
                        "allowed": False,
                        "reason": f"Action '{action}' requires role '{required_role.title()}', but user has role '{user_role.title() if user_role else 'none'}'",
                        "metadata": {
                            "constraint_type": "role_based_owl",
                            "required_role": required_role,
                            "user_role": user_role,
                            "rule_uri": rule.get("uri", "")
                        }
                    }

            # Check 2: requiresApproval from OWL
            if "requiresApproval" in rule:
                approver_role = rule["requiresApproval"].lower()
                has_approval = context.get("approved_by", "").lower() == approver_role
                if not has_approval and user_role != approver_role and user_role != "admin":
                    return {
                        "allowed": False,
                        "reason": f"Action '{action}' requires approval from '{approver_role.title()}'",
                        "metadata": {
                            "constraint_type": "approval_required",
                            "requires_approval": approver_role,
                            "rule_uri": rule.get("uri", "")
                        }
                    }

            # Check 3: appliesTo entity type
            if "appliesTo" in rule:
                applies_to = rule["appliesTo"].lower()
                if entity_lower != applies_to and applies_to not in entity_lower and entity_lower not in applies_to:
                    return {
                        "allowed": False,
                        "reason": f"Action '{action}' can only be applied to '{applies_to.title()}', not '{entity}'",
                        "metadata": {
                            "constraint_type": "entity_type_mismatch",
                            "applies_to": applies_to,
                            "provided_entity": entity_lower,
                            "rule_uri": rule.get("uri", "")
                        }
                    }

        # Legacy: Check if context has required_role (backwards compatibility)
        if "required_role" in context:
            required_role = context["required_role"].lower()
            if user_role != "admin" and user_role != required_role:
                return {
                    "allowed": False,
                    "reason": f"Action requires role '{required_role}', but user has role '{user_role}'",
                    "metadata": {"constraint_type": "role_based_context"}
                }

        return {"allowed": True}

    def _find_action_rule(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Find the action rule for a given action name.

        Tries exact match first, then partial matching.
        """
        # Exact match
        if action_name in self._action_rules:
            return self._action_rules[action_name]

        # Partial match (e.g., "delete user" matches "delete user")
        for rule_name, rule in self._action_rules.items():
            if action_name in rule_name or rule_name in action_name:
                return rule

        return None
    
    def _suggest_similar_actions(self, action: str) -> List[str]:
        """Suggest similar actions if the requested action doesn't exist."""
        if self.graph is None:
            return []
        
        # Simple similarity check - look for actions with similar names
        suggestions = []
        action_lower = action.lower()
        
        # This is a simplified implementation
        # In practice, you might use string similarity algorithms
        for term in self.graph.all_nodes():
            if isinstance(term, URIRef):
                term_str = str(term)
                # Extract potential action names
                if any(keyword in term_str.lower() for keyword in ['action', 'operation', 'method']):
                    label = self._get_label(term)
                    if label and action_lower[:3] in label.lower():
                        suggestions.append(label)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _find_actions_for_entity_simple(self, entity: str) -> List[str]:
        """
        Find actions for an entity using parsed action rules.

        Returns only actions from _action_rules that have matching appliesTo,
        or all known actions if no appliesTo filtering is possible.
        """
        if not self._action_rules:
            return []

        entity_lower = entity.lower().strip()
        actions = []

        # Filter actions by appliesTo property
        for action_name, rule in self._action_rules.items():
            applies_to = rule.get("appliesTo", "").lower()

            # Include action if:
            # 1. appliesTo matches entity (exact or partial)
            # 2. No appliesTo defined (action applies to all)
            if not applies_to or applies_to == entity_lower or entity_lower in applies_to or applies_to in entity_lower:
                actions.append(action_name)

        # If no actions found with appliesTo filter, return all known actions
        if not actions and self._known_actions:
            return list(self._known_actions)

        return actions
    
    def _get_label(self, resource: URIRef) -> Optional[str]:
        """Get the label (rdfs:label) for a resource, or extract from URI."""
        if self.graph is None:
            return None
        
        # Try to get rdfs:label
        for label in self.graph.objects(resource, RDFS.label):
            if isinstance(label, Literal):
                return str(label)
        
        # Fallback: extract from URI
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
            # Fallback: extract from URI string
            if '#' in action_uri:
                return action_uri.split('#')[-1]
            elif '/' in action_uri:
                return action_uri.split('/')[-1]
            return None
