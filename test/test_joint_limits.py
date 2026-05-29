# Copyright 2025 Sentience Robotics Team
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every actuated joint must declare a usable <limit> block."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from xacro_helper import run_xacro


def _paths():
    root = Path(__file__).resolve().parents[1]
    return (
        root / "description/urdf/inmoov.urdf.xacro",
        root / "description",
        root / "config/controllers.yaml",
        root / "config/hardware/active.yaml",
    )


def _expand_urdf() -> ET.Element:
    urdf_xacro, base, controllers, _ = _paths()
    r = run_xacro(
        [
            str(urdf_xacro),
            f"base_path:={base}",
            f"controller_config:={controllers}",
            "use_gazebo_sim:=false",
            "use_mock_hardware:=true",
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    return ET.fromstring(r.stdout)


@pytest.fixture(scope="module")
def urdf_root():
    return _expand_urdf()


@pytest.fixture(scope="module")
def actuated_joint_names():
    _, _, _, active = _paths()
    data = yaml.safe_load(active.read_text(encoding="utf-8"))
    return {a["urdf_joint"] for a in data["actuators"]}


def test_actuated_joints_have_limits(urdf_root, actuated_joint_names):
    """Each actuated joint must have a <limit> with non-degenerate bounds."""
    found: set[str] = set()
    for joint in urdf_root.findall("joint"):
        name = joint.get("name")
        if name not in actuated_joint_names:
            continue
        found.add(name)
        limit = joint.find("limit")
        assert limit is not None, f"missing <limit> on actuated joint {name}"
        lower = float(limit.get("lower"))
        upper = float(limit.get("upper"))
        assert upper > lower, f"{name} has degenerate limit lower={lower} upper={upper}"
        for attr in ("effort", "velocity"):
            assert float(limit.get(attr)) > 0, f"{name} non-positive {attr}"
    missing = actuated_joint_names - found
    assert not missing, f"actuators in active.yaml not present in URDF: {sorted(missing)}"


def test_model_scale_property_resolves(urdf_root):
    """xacro should fully expand model_scale (no leftover ${...} tokens)."""
    text = ET.tostring(urdf_root, encoding="unicode")
    assert "${model_scale" not in text, "model_scale property left unevaluated"
