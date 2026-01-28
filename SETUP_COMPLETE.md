# OntoGuard-AI - Setup Complete

## Установка завершена: 2026-01-27

### Что установлено

**OntoGuard** - семантический фреймворк валидации для защиты AI-агентов от нарушений бизнес-правил с использованием OWL-онтологий.

### Ключевые компоненты

| Компонент | Описание |
|-----------|----------|
| **rdflib** | Работа с RDF/OWL онтологиями |
| **fastmcp** | MCP сервер для интеграции с Claude |
| **pydantic** | Валидация данных |
| **rich** | Красивый вывод в терминале |
| **click** | CLI интерфейс |

### Расположение

- **Репозиторий**: `~/ontoguard-ai/`
- **Онтологии**: `~/ontoguard-ai/examples/ontologies/`
  - `ecommerce.owl` - E-Commerce (заказы, возвраты, пользователи)
  - `finance.owl` - Финансы (транзакции, compliance)
  - `healthcare.owl` - Здравоохранение (HIPAA, доступ к данным)
- **Конфигурация**: `~/ontoguard-ai/config.yaml`

### MCP Сервер

**Добавлен в**: `~/.claude.json` (секция mcpServers)

**Конфигурация**:
```json
"ontoguard": {
  "type": "stdio",
  "command": "python",
  "args": ["-m", "ontoguard.mcp_server"],
  "env": {
    "ONTOGUARD_CONFIG": "/home/vladspace_ubuntu24/ontoguard-ai/config.yaml"
  }
}
```

### MCP Tools (4 инструмента)

| Tool | Описание |
|------|----------|
| `validate_action` | Валидация действия перед выполнением |
| `get_allowed_actions` | Список разрешённых действий для entity |
| `explain_rule` | Объяснение бизнес-правила |
| `check_permissions` | Проверка прав доступа для роли |

### Использование

#### 1. Через Python

```python
from ontoguard import OntologyValidator

validator = OntologyValidator("path/to/ontology.owl")

result = validator.validate(
    action="process_refund",
    entity="Refund",
    entity_id="refund_123",
    context={"role": "Customer", "amount": 5000}
)

if result.allowed:
    execute_action()
else:
    print(f"Blocked: {result.reason}")
```

#### 2. Через CLI

```bash
# Валидация действия
cd ~/ontoguard-ai
python -m ontoguard validate examples/ontologies/ecommerce.owl \
  --action "delete user" \
  --entity "User" \
  --role "Admin"

# Информация об онтологии
python -m ontoguard info examples/ontologies/ecommerce.owl --detailed
```

#### 3. Через MCP (после перезапуска Claude Code)

```
# Claude автоматически использует ontoguard tools:
"Проверь, может ли Customer удалить User"
"Какие действия доступны для Order?"
"Объясни правило ProcessRefund"
```

### Примеры онтологий

#### E-Commerce Rules:
- Только Admin может удалять пользователей
- Возвраты > $1000 требуют Manager approval
- Заказы можно отменить только в течение 24 часов

#### Healthcare Rules (HIPAA):
- Только Doctor/Nurse могут читать медицинские записи
- Audit trail для всех операций
- Time-based access controls

#### Finance Rules:
- KYC проверка для транзакций > $10,000
- International transfers требуют Manager approval
- Compliance constraints

### Тестирование

```bash
cd ~/ontoguard-ai

# Запуск всех тестов
pytest tests/

# Базовый пример
python examples/basic_usage.py

# MCP интеграция
python examples/mcp_integration.py
```

### Следующие шаги

1. **Перезапустить Claude Code** для активации MCP сервера
2. **Протестировать tools** через Claude: "Проверь permissions для Customer на delete user"
3. **Создать свою онтологию** для специфических бизнес-правил

### Ресурсы

- **GitHub**: https://github.com/cloudbadal007/ontoguard-ai
- **Документация**: `~/ontoguard-ai/docs/`
- **Примеры**: `~/ontoguard-ai/examples/`
