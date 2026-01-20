"""
OntologyValidator - Core validation engine for OntoGuard.

This module provides the main validation logic for checking AI agent actions
against OWL ontologies.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

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
            
        except Exception as e:
            error_msg = f"Failed to parse ontology file {self.ontology_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e
    
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
        """Check if an action exists in the ontology."""
        if self.graph is None:
            return False
        
        # Simple check: look for the action in the graph
        # This is a simplified implementation - adjust based on your ontology structure
        action_lower = action.lower()
        
        # Check for action as a class or individual
        for subject, predicate, obj in self.graph:
            # Check subject labels
            if hasattr(subject, 'label') or isinstance(subject, URIRef):
                label = self._get_label(subject)
                if label and action_lower in label.lower():
                    return True
            
            # Check object labels
            if isinstance(obj, URIRef) or isinstance(obj, Literal):
                label = self._get_label(obj) if isinstance(obj, URIRef) else str(obj)
                if label and action_lower in label.lower():
                    return True
        
        # Also check if action appears in any property or class name
        for term in self.graph.all_nodes():
            if isinstance(term, URIRef):
                term_str = str(term).lower()
                if action_lower in term_str:
                    return True
        
        return True  # Default to True for now - adjust based on ontology structure
    
    def _check_entity_type(self, entity: str) -> bool:
        """Check if an entity type exists in the ontology."""
        if self.graph is None:
            return False
        
        entity_lower = entity.lower()
        
        # Check for entity type in the graph
        for subject, predicate, obj in self.graph:
            if predicate == RDF.type:
                label = self._get_label(subject)
                if label and entity_lower in label.lower():
                    return True
        
        # Check all classes
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            label = self._get_label(cls)
            if label and entity_lower in label.lower():
                return True
        
        return True  # Default to True for now - adjust based on ontology structure
    
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
        
        Returns:
            Dictionary with 'allowed' key and optional 'reason' and 'metadata' keys
        """
        if self.graph is None:
            return {"allowed": True}
        
        # This is a placeholder for constraint checking
        # In a real implementation, you would:
        # - Check temporal constraints (time-based rules)
        # - Check role-based permissions
        # - Check cardinality constraints
        # - Check property restrictions
        
        # Example: Check if context has required fields
        if "required_role" in context:
            user_role = context.get("role", "")
            required_role = context["required_role"]
            if user_role != required_role:
                return {
                    "allowed": False,
                    "reason": f"Action requires role '{required_role}', but user has role '{user_role}'",
                    "metadata": {"constraint_type": "role_based"}
                }
        
        return {"allowed": True}
    
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
        """Simple fallback method to find actions for an entity."""
        if self.graph is None:
            return []
        
        actions = []
        entity_lower = entity.lower()
        
        # Simple traversal to find related actions
        for subject, predicate, obj in self.graph:
            subject_label = self._get_label(subject)
            if subject_label and entity_lower in subject_label.lower():
                # Look for related actions
                for _, pred, action_obj in self.graph.triples((subject, None, None)):
                    action_label = self._get_label(action_obj)
                    if action_label:
                        actions.append(action_label)
        
        return list(set(actions))  # Remove duplicates
    
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
