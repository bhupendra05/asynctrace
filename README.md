# asynctrace

> **Full caller context in asyncio exceptions — fix useless async stack traces**

[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![PyPI](https://img.shields.io/pypi/v/asynctrace)](https://pypi.org/project/asynctrace)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Install

```bash
pip install asynctrace
```

## The problem

When an `asyncio` task raises an exception, the traceback shows what happened *inside* the task — but not *where in your code* the task was created. The original caller context is gone.

```
# Without asynctrace: 
Task exception was never retrieved
Traceback (most recent call last):
  File "asyncio/tasks.py", line 258, in __step
  ...
ValueError: something broke
# (no idea who created this task or why)
```

## Usage

```python
import asyncio
import asynctrace

asynctrace.install()  # one line — patches globally

async def fetch_user(user_id):
    raise ValueError(f"User {user_id} not found")

async def main():
    await asyncio.create_task(fetch_user(42))

asyncio.run(main())
# Now shows:
# ValueError: User 42 not found
#
# --- Task created at ---
# File "main.py", line 9, in main
#   await asyncio.create_task(fetch_user(42))
```

### Per-function decorator

```python
from asynctrace import traced

@traced
async def fetch_order(order_id: int):
    result = await db.get(order_id)  # any exception here shows full context
    return result
```

## Architecture

```
asynctrace/
├── asynctrace/
│   ├── __init__.py   # public API
│   └── *.py          # core implementation
└── tests/
    └── test_*.py     # 2 passed — no API key needed
```

## License

MIT © [bhupendra05](https://github.com/bhupendra05)

---

*Part of the [bhupendra05 developer tools collection](https://github.com/bhupendra05)*
