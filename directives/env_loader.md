# Environment Loader Directive

## Goal
Provide automatic loading of environment variables from `.env` files for all execution scripts in the agent workflow system.

## Inputs
- `.env` file containing key-value pairs
- Optional custom path to `.env` file

## Tools/Scripts

### Primary Script
| Script | Purpose |
|--------|---------|
| `execution/env_loader.py` | Loads environment variables from `.env` file into `os.environ` |

## Outputs
- Environment variables loaded into `os.environ`
- Dictionary of loaded key-value pairs returned from `load_env()`

---

## Function: load_env()

```python
def load_env(env_path: str = None) -> dict
```

### Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `env_path` | `str` or `None` | `None` | Path to `.env` file. If `None`, defaults to `.env` in project root (parent of `execution/` folder) |

### Returns
- `dict`: Dictionary of loaded environment variables `{key: value}`
- Returns empty dict `{}` if `.env` file does not exist

### Behavior

**Default Path Resolution:**
```
execution/env_loader.py  -->  parent directory  -->  .env
```
Uses `Path(__file__).parent.parent / ".env"` to find the project root `.env` file.

**Parsing Rules:**
1. Empty lines are skipped
2. Lines starting with `#` are treated as comments and skipped
3. Lines must contain `=` to be parsed
4. Key and value are split on first `=` only (values can contain `=`)
5. Both key and value are stripped of whitespace
6. Surrounding quotes (`"` or `'`) are removed from values

### Usage

**Method 1: Explicit call (recommended)**
```python
from env_loader import load_env
load_env()  # Load from default location

# Or with custom path
load_env("/path/to/custom/.env")
```

**Method 2: Auto-load on import**
```python
import env_loader  # Automatically loads .env on import
```

**Typical pattern in execution scripts:**
```python
# At the very top of your script
from env_loader import load_env
load_env()

# Now environment variables are available
import os
api_key = os.getenv("API_KEY")
```

---

## .env File Format

### Supported Syntax
```env
# This is a comment
KEY=value
ANOTHER_KEY=another value

# Quoted values (quotes are stripped)
QUOTED="value with spaces"
SINGLE_QUOTED='single quoted value'

# Values with equals signs
CONNECTION_STRING=host=localhost;port=5432

# Whitespace handling
  PADDED_KEY  =  padded value
# Result: key="PADDED_KEY", value="padded value"
```

### Example .env File
```env
# Slack configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
SLACK_CHANNEL=#agent-notifications
SLACK_ENABLED=true
SLACK_USERNAME=Agent Workflow
SLACK_ICON=:robot_face:

# Observability configuration
OBSERVABILITY_CONSOLE=true
OBSERVABILITY_FILE=true
LOG_DIR=.tmp/logs

# API keys
OPENAI_API_KEY=sk-...
```

---

## Edge Cases

### File Not Found
- If `.env` file does not exist at the specified path, function returns empty dict `{}`
- No error is raised
- Execution continues normally

### Empty File
- Returns empty dict `{}`

### Malformed Lines
- Lines without `=` are silently skipped
- No error is raised

### Quote Handling
- Only matching pairs of quotes are stripped: `"value"` or `'value'`
- Mismatched quotes are preserved: `"value'` stays as `"value'`
- Only outermost quotes are removed: `"'value'"` becomes `'value'`

### Existing Environment Variables
- Variables loaded from `.env` will **overwrite** existing `os.environ` values
- No merge or protection of existing values

### Auto-Load on Import
- The module calls `load_env()` automatically when imported
- The result is stored in module variable `_loaded`
- Subsequent imports do not re-load (Python module caching)

### Multiple Calls
- Calling `load_env()` multiple times is safe
- Each call re-reads and re-applies the `.env` file
- Use different paths to load multiple `.env` files

---

## Dependencies

- `os` - for `os.environ` manipulation
- `pathlib.Path` - for path resolution

No external dependencies required.

---

## Integration Notes

### Import Order
Always import and call `env_loader` **before** importing modules that rely on environment variables:

```python
# CORRECT ORDER
from env_loader import load_env
load_env()

from slack_notifier import SlackNotifier  # Uses SLACK_WEBHOOK_URL from env

# INCORRECT ORDER - may fail or use wrong values
from slack_notifier import SlackNotifier  # SLACK_WEBHOOK_URL not yet loaded!
from env_loader import load_env
load_env()
```

### Multiple Environment Files
```python
from env_loader import load_env

# Load base configuration
load_env(".env")

# Load environment-specific overrides
load_env(".env.local")  # Overwrites any duplicate keys
```

---

## Self-Annealing Notes

### Learnings
_Add discoveries here as the system evolves:_

1. _Example: "Some CI systems require .env.ci for different paths"_

### Common Issues
_Document recurring problems and solutions:_

1. _Example: "Module import order matters - always import env_loader first"_

---

## Setup Checklist

1. [ ] Create `.env` file in project root
2. [ ] Add `.env` to `.gitignore` (do not commit secrets)
3. [ ] Create `.env.example` with placeholder values for documentation
4. [ ] Import `env_loader` at top of all execution scripts
