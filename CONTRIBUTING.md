# Contributing

Contributions welcome — especially toward the roadmap items in the README
(real optical flow, connectome backend, tested firmware).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

```bash
ruff check .
pytest -q
python -m wormdrive.main --synthetic --dry-run --steps 20
```

## Ground rules

- Keep the honesty policy: no fabricated simulation results, no neuron
  claims beyond what's implemented, stubs must fail loudly rather than
  fake output.
- The receiver-side watchdog contract (zero motors after 500ms silence)
  must never be weakened.
- New behavior needs a test.
