import json, pathlib

def test_config_json_types():
    p = pathlib.Path("config.json")
    if not p.exists():
        return
    cfg = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(cfg.get("verified_only", False), bool)
    assert isinstance(cfg.get("fiat", "ARS"), str)
    assert isinstance(cfg.get("margins", {}), dict)
