import pytest

from wormdrive.config import Config, load_config


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_empty_file_gives_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("")
    cfg = load_config(p)
    assert cfg.robot_ip == Config.robot_ip
    assert cfg.motor.limit == 1.0


def test_full_config_parses(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "robot_ip: 10.0.0.5\nrobot_port: 8000\npc_port: 8001\nbackend: mock\n"
        "motor:\n  limit: 0.5\n  smoothing: 0.2\n  invert: true\n"
        "vision:\n  fps: 60\n"
    )
    cfg = load_config(p)
    assert cfg.robot_ip == "10.0.0.5"
    assert cfg.robot_port == 8000
    assert cfg.motor.limit == 0.5
    assert cfg.motor.invert is True
    assert cfg.vision.fps == 60


def test_unknown_key_warns_but_loads(tmp_path, capsys):
    p = tmp_path / "c.yaml"
    p.write_text("robot_ip: 1.2.3.4\nfuture_feature: 42\n")
    cfg = load_config(p)
    assert cfg.robot_ip == "1.2.3.4"
    assert "future_feature" in capsys.readouterr().err


def test_invalid_backend_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("backend: quantum\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_invalid_smoothing_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("motor:\n  smoothing: 2.0\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_non_mapping_root_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("- just\n- a\n- list\n")
    with pytest.raises(TypeError):
        load_config(p)
