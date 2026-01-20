# OntoGuard

**The Semantic Firewall for AI Agents**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/yourusername/ontoguard)
[![PyPI version](https://img.shields.io/pypi/v/ontoguard)](https://pypi.org/project/ontoguard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/yourusername/ontoguard)](https://github.com/yourusername/ontoguard)

> **Stop AI agents from making costly mistakes. Validate every action against your business rules before execution.**

---

## The Problem

AI agents are powerful, but they make mistakes—expensive ones. In production systems, these errors can lead to:

- **$4.6M in unauthorized transactions** (real-world example: AI agent processed refunds without proper approval)
- **Data corruption** from incorrect schema mappings
- **Compliance violations** when agents bypass business rules
- **Security breaches** from unauthorized actions

The gap between demos and production is vast. While AI agents excel at understanding natural language and making decisions, they struggle with:

- **Semantic validation** - Understanding what actions are actually allowed
- **Business rule enforcement** - Following complex organizational policies
- **Schema consistency** - Maintaining data integrity across operations
- **Context awareness** - Applying the right rules at the right time

Traditional validation approaches don't work well with AI agents because they're too rigid, require extensive code changes, and can't adapt to the dynamic nature of agent behavior.

---

## The Solution

**OntoGuard** is a semantic firewall that validates AI agent actions against OWL ontologies before they execute. It acts as a safety layer between your agents and your systems, ensuring every action complies with your business rules.

### Architecture

```
┌─────────────────┐
│   AI Agent      │
│  (LLM-based)    │
└────────┬─────────┘
         │ Action Request
         ▼
┌─────────────────┐
│   OntoGuard     │  ◄─── OWL Ontology
│   Validator     │      (Business Rules)
└────────┬────────┘
         │ Validated Action
         ▼
┌─────────────────┐
│  Your System    │
│  (Database/API) │
└─────────────────┘
```

### Key Benefits

- ✅ **Prevent Costly Errors** - Catch violations before they cause damage
- ✅ **Zero Code Changes** - Works with any AI agent framework
- ✅ **Business Rule Enforcement** - Define rules in OWL, enforce automatically
- ✅ **Self-Healing** - Automatically corrects schema mapping errors
- ✅ **Production Ready** - Battle-tested validation engine
- ✅ **Framework Agnostic** - Works with LangChain, AutoGPT, CrewAI, and more

---

## Quick Start (30 seconds)

### Installation

```bash
pip install ontoguard
```

### Minimal Example

```python
from ontoguard import OntologyValidator

# Load your business rules
validator = OntologyValidator("business_rules.owl")

# Validate an action before execution
result = validator.validate(
    action="process_refund",
    entity="Refund",
    entity_id="refund_123",
    context={"role": "Customer", "amount": 5000}
)

if result.allowed:
    # Safe to proceed
    process_refund(result.metadata)
else:
    # Blocked - show reason
    print(f"Denied: {result.reason}")
    print(f"Alternatives: {result.suggested_actions}")
```

**That's it!** Your agent is now protected by semantic validation.

---

## Features

### 🔒 Core Validation

Validate any action against your ontology before execution. OntoGuard checks:
- Action existence and validity
- Entity type compatibility
- Role-based permissions
- Business rule constraints
- Temporal and contextual rules

### 📋 Business Rule Enforcement

Define complex business rules in OWL ontologies:
- **Role-based access control** - "Only Admins can delete users"
- **Amount thresholds** - "Refunds over $1000 require Manager approval"
- **Temporal constraints** - "Orders can only be cancelled within 24 hours"
- **Custom rules** - Define any constraint your business needs

### 🔧 Self-Healing Schema Mapping

Automatically corrects schema mismatches between agent actions and your data model:
- Maps agent terminology to your schema
- Suggests corrections for invalid field names
- Learns from successful mappings

### 🔌 MCP Integration (Coming Soon)

Native integration with Model Context Protocol for seamless agent workflows.

### 🎯 Multi-Framework Support

Works with any AI agent framework:
- LangChain / LangGraph
- AutoGPT
- CrewAI
- BabyAGI
- Custom frameworks

---

## Usage Examples

### Command Line Interface

**Validate a single action:**
```bash
ontoguard validate ecommerce.owl \
  --action "create order" \
  --entity "Order" \
  --role "Customer"
```

**Interactive mode:**
```bash
ontoguard interactive ecommerce.owl
```

**Show ontology information:**
```bash
ontoguard info ecommerce.owl --detailed
```

### Programmatic Usage

**Basic validation:**
```python
from ontoguard import OntologyValidator, ValidationResult

validator = OntologyValidator("rules.owl")

result = validator.validate(
    action="delete_user",
    entity="User",
    entity_id="user_123",
    context={"role": "Admin"}
)

print(f"Allowed: {result.allowed}")
print(f"Reason: {result.reason}")
```

**Get allowed actions:**
```python
# Query what actions are allowed for an entity
allowed = validator.get_allowed_actions("Order", {"role": "Customer"})
print(f"Customer can: {allowed}")
```

**Explain denials:**
```python
# Get detailed explanation for denied actions
explanation = validator.explain_denial(
    action="delete_user",
    entity="User",
    context={"role": "Customer"}
)
print(explanation)
```

### Integration Example

```python
from ontoguard import OntologyValidator
from langchain.agents import AgentExecutor

# Initialize validator
validator = OntologyValidator("business_rules.owl")

# Wrap your agent's action execution
def safe_execute(action, entity, context):
    result = validator.validate(action, entity, context.get("entity_id", ""), context)
    
    if not result.allowed:
        return {
            "error": result.reason,
            "suggested_actions": result.suggested_actions
        }
    
    # Proceed with actual execution
    return execute_action(action, entity, context)

# Use in your agent
agent = AgentExecutor(
    tools=[safe_execute],
    # ... other config
)
```

---

## Documentation

- 📖 **[Getting Started Guide](docs/getting-started.md)** - Complete setup and configuration
- 📚 **[API Reference](docs/api-reference.md)** - Detailed API documentation
- 💡 **[Examples](examples/)** - Real-world usage examples
- ❓ **[FAQ](docs/faq.md)** - Common questions and answers

### Quick Links

- [Installation Guide](docs/installation.md)
- [Creating Ontologies](docs/creating-ontologies.md)
- [Business Rules Guide](docs/business-rules.md)
- [Integration Examples](examples/)

---

## Contributing

We welcome contributions! Here's how you can help:

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ontoguard.git
cd ontoguard

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
ruff check src tests
black src tests
```

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** with tests
4. **Run the test suite** (`pytest tests/`)
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

### Areas for Contribution

- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🧪 Test coverage
- 🎨 UI/UX improvements
- 🌐 Additional framework integrations

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

**Pankaj Kumar**

AI Engineer and Semantic Web enthusiast. Building tools to make AI agents safer and more reliable in production environments.

- 📝 [Medium Articles](https://medium.com/@yourusername) - Read about AI safety, semantic validation, and production AI systems
- 💼 [LinkedIn](https://linkedin.com/in/yourusername)
- 🐦 [Twitter](https://twitter.com/yourusername)
- 📧 Email: your.email@example.com

### Related Articles

- [Why AI Agents Fail in Production (And How to Fix It)](https://medium.com/@yourusername/why-ai-agents-fail)
- [Building a Semantic Firewall for AI Agents](https://medium.com/@yourusername/semantic-firewall)
- [The $4.6M Mistake: A Case Study in AI Agent Validation](https://medium.com/@yourusername/4.6m-mistake)

---

## Acknowledgments

- Built with [rdflib](https://github.com/RDFLib/rdflib) for ontology processing
- Inspired by the need for safer AI agent deployments
- Thanks to all contributors and users

---

## Star History

If you find OntoGuard useful, please consider giving it a star ⭐ on GitHub!

---

**Made with ❤️ for the AI community**

*Preventing costly mistakes, one validation at a time.*
