import pytest


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Isola `etl/` numa pasta temporária (brutos/, trabalho/, .env)."""
    monkeypatch.setenv("MUNINN_ETL_BASE", str(tmp_path))
    return tmp_path
