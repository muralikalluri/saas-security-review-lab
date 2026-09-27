"""Deliberately insecure for demonstration. Do not deploy."""

from isolation_tester.config import load_config


def test_load_config_interpolates_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("API_BASE", "http://example.invalid:9999")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
base_url: "${API_BASE:http://localhost:8183}"
tenants:
  - id: tenant-a
    name: Tenant A
    users:
      owner: {username: alice, password: pw}
    fixtures:
      invoice_ids: [1]
"""
    )
    config = load_config(config_file)
    assert config.base_url == "http://example.invalid:9999"
    assert config.tenants[0].id == "tenant-a"


def test_load_config_uses_default_when_env_var_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("API_BASE", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
base_url: "${API_BASE:http://localhost:8183}"
tenants:
  - id: tenant-a
    name: Tenant A
    users:
      owner: {username: alice, password: pw}
"""
    )
    config = load_config(config_file)
    assert config.base_url == "http://localhost:8183"
