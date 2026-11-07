"""Entry point seed dari dalam paket API.

Memuat ``packages/database/seeds/seed.py`` tanpa menyalin logikanya:

    cd apps/api && PYTHONPATH=. python -m app.seed --reset
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_seed_module():
    root = Path(__file__).resolve().parents[3]
    seed_path = root / "packages" / "database" / "seeds" / "seed.py"
    spec = importlib.util.spec_from_file_location("dextra_database_seed", seed_path)
    if spec is None or spec.loader is None:  # pragma: no cover - salah konfigurasi
        raise RuntimeError(f"Tidak bisa memuat seed dari {seed_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    _load_seed_module().main()


if __name__ == "__main__":
    main()
