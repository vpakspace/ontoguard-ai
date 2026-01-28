# OntoGuard AI - Project Memory

Semantic Firewall for AI Agents based on OWL Ontologies

**Создан**: 2026-01-27
**GitHub**: https://github.com/vpakspace/ontoguard-ai

---

## Обзор проекта

OntoGuard AI - семантический файрвол для AI-агентов, использующий OWL (Web Ontology Language) онтологии для валидации действий на основе ролей и бизнес-правил.

### Ключевые возможности

- **OWL Ontology Validation** - парсинг и валидация на основе RDFLib
- **Role-Based Access Control** - RBAC через OWL классы и свойства
- **MCP Server** - интеграция с Claude Code через FastMCP
- **Ownership Validation** - правила "own" (Patient can read own MedicalRecord)
- **Role Aliasing** - синонимы ролей (labtech ↔ labtechnician)

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (FastMCP)                     │
│  Tools: validate_action, check_permissions,                 │
│         get_allowed_actions, explain_rule                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 OntologyValidator                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │ ParsedRule      │  │ Rule Matching Algorithm         │   │
│  │ - action        │  │ - Role aliasing                 │   │
│  │ - entity        │  │ - Ownership validation          │   │
│  │ - role          │  │ - O(1) indexed lookup           │   │
│  │ - requires_own  │  │ - Constraint checking           │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 RDFLib OWL Parser                            │
│  - Load .owl files (Turtle, RDF/XML)                        │
│  - Parse action rules (requiresRole, appliesTo)             │
│  - Extract role hierarchy                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Структура проекта

```
ontoguard-ai/
├── src/ontoguard/
│   ├── __init__.py
│   ├── validator.py      # OntologyValidator, ParsedRule
│   ├── mcp_server.py     # FastMCP server
│   └── models.py         # Pydantic models
├── ontologies/
│   └── ecommerce.owl     # E-commerce domain ontology
├── tests/
│   ├── test_validator.py
│   └── test_mcp_server.py
├── config.yaml           # MCP server configuration
├── pyproject.toml
└── README.md
```

---

## OWL Ontology Structure

### Action Rules в OWL

```turtle
:DoctorReadPatientRecord a owl:Class ;
    rdfs:subClassOf :ActionRule ;
    :requiresRole :Doctor ;
    :appliesTo :PatientRecord ;
    :allowsAction "read" .
```

### Role Hierarchy

```
Admin
├── Doctor
├── Nurse
├── LabTechnician (alias: LabTech)
├── Receptionist
├── InsuranceAgent (alias: Insurance)
└── Patient
```

### Ownership Rules

```turtle
:PatientReadOwnMedicalRecord a owl:Class ;
    :requiresRole :Patient ;
    :appliesTo :MedicalRecord ;
    :allowsAction "read" ;
    :requiresOwnership true .
```

---

## Rule Matching Algorithm

### ParsedRule Class

```python
@dataclass
class ParsedRule:
    action: str           # read, create, update, delete
    entity: str           # PatientRecord, MedicalRecord, etc.
    role: str             # Doctor, Nurse, Admin
    requires_ownership: bool  # "own" in entity name
```

### Role Aliasing

```python
ROLE_ALIASES = {
    'labtechnician': 'labtech',
    'labtech': 'labtechnician',
    'insuranceagent': 'insurance',
    'insurance': 'insuranceagent',
}
```

### Matching Logic

1. Normalize role (lowercase + aliases)
2. Build key: `{action}:{entity}:{role}`
3. O(1) lookup in indexed rules
4. Check ownership if required
5. Return ValidationResult

---

## MCP Server Tools

| Tool | Описание |
|------|----------|
| `validate_action` | Валидация действия (action, entity, context) |
| `check_permissions` | Проверка разрешений роли |
| `get_allowed_actions` | Список разрешённых действий для роли |
| `explain_rule` | Объяснение правила из OWL |

### Конфигурация MCP

```yaml
# config.yaml
ontology_paths:
  - ontologies/ecommerce.owl
default_policy: deny
cache_enabled: true
```

### Запуск MCP Server

```bash
# Напрямую
python -m ontoguard.mcp_server

# Через Claude Code (~/.claude.json)
"ontoguard": {
  "command": "python",
  "args": ["-m", "ontoguard.mcp_server"],
  "env": {
    "ONTOGUARD_CONFIG": "/path/to/config.yaml"
  }
}
```

---

## Тестирование

### Rule Matching Tests (12/12 passed)

| Тест | Результат |
|------|-----------|
| Admin delete PatientRecord | ✅ allowed |
| Doctor read PatientRecord | ✅ allowed |
| Nurse read PatientRecord | ✅ allowed |
| Nurse delete PatientRecord | ✅ denied |
| LabTech read LabResult | ✅ allowed |
| LabTechnician read LabResult | ✅ allowed (alias) |
| InsuranceAgent read Billing | ✅ allowed |
| Insurance read Billing | ✅ allowed (alias) |
| Receptionist create Appointment | ✅ allowed |
| Receptionist delete MedicalRecord | ✅ denied |
| Patient read own MedicalRecord | ✅ allowed (ownership) |
| Doctor update PatientRecord | ✅ denied (OWL rule) |

### Запуск тестов

```bash
pytest tests/ -v
# 244 tests passing
```

---

## Интеграции

### Universal Agent Connector

OntoGuard интегрирован в UAC для валидации SQL queries:

```python
# В routes.py
adapter = get_ontoguard_adapter()
result = adapter.validate_action(action, entity_type, context)
if not result.allowed:
    return jsonify({'error': 'Denied by OntoGuard'}), 403
```

### Claude Code MCP

OntoGuard доступен как MCP server в Claude Code:
- Status: ✅ Connected (16 серверов)
- Tools: 4 (validate_action, check_permissions, get_allowed_actions, explain_rule)

---

## Commits (2026-01-27/28)

| Commit | Описание |
|--------|----------|
| `013388b` | fix: OWL Rule Parsing (requiresRole, appliesTo) |
| `61f0a0d` | feat: Enhance rule matching algorithm for 100% accuracy |
| `ebd1bd1` | docs: Add setup documentation and config |

---

## TODO

- [ ] Добавить кэширование правил
- [ ] Поддержка нескольких онтологий
- [ ] WebSocket API для real-time validation
- [ ] Admin UI для управления правилами
- [ ] Prometheus metrics

---

## Связанные проекты

- **Universal Agent Connector**: `~/universal-agent-connector/`
- **Hospital OWL**: `~/universal-agent-connector/ontologies/hospital.owl`

---

**Последнее обновление**: 2026-01-28
