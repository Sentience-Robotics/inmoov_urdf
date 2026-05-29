# Copyright 2025 Sentience Robotics Team
# SPDX-License-Identifier: GPL-3.0-or-later

"""Unit tests for scripts/scale_xacro_origins.py + production xacro coverage."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
URDF_XACRO = ROOT / "description/robot_description/urdf/robot_description.urdf.xacro"


def _load():
    path = SCRIPTS / "scale_xacro_origins.py"
    spec = importlib.util.spec_from_file_location("scale_xacro_origins", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scale_xacro_origins"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


SAMPLE = """\
<robot>
  <joint name="j">
    <origin rpy="0 0 0" xyz="1.5 0.0 -2.25"/>
  </joint>
  <link name="L">
    <visual>
      <geometry>
        <mesh filename="${mesh_dir}/foo.dae" scale="1.00000 1.00000 1.00000"/>
      </geometry>
    </visual>
    <collision>
      <geometry><box size="0.4 0.3 0.2"/></geometry>
    </collision>
    <collision>
      <geometry><cylinder length="0.35" radius="0.12"/></geometry>
    </collision>
    <collision>
      <geometry><sphere radius="0.18"/></geometry>
    </collision>
  </link>
</robot>
"""


def test_origin_xyz_wrapped(mod):
    out = mod._transform(SAMPLE)
    assert 'xyz="${model_scale * 1.5} ${model_scale * 0.0} ${model_scale * -2.25}"' in out


def test_box_size_wrapped(mod):
    out = mod._transform(SAMPLE)
    assert (
        'size="${model_scale * 0.4} ${model_scale * 0.3} ${model_scale * 0.2}"' in out
    )


def test_cylinder_dimensions_wrapped(mod):
    out = mod._transform(SAMPLE)
    assert 'length="${model_scale * 0.35}"' in out
    assert 'radius="${model_scale * 0.12}"' in out


def test_sphere_radius_wrapped(mod):
    out = mod._transform(SAMPLE)
    assert 'radius="${model_scale * 0.18}"' in out


def test_mesh_scale_wrapped(mod):
    """Without this, joint frames shrink but DAEs stay full size — the stand
    misaligns with the torso (regression seen on Lucy URDF)."""
    out = mod._transform(SAMPLE)
    assert (
        'scale="${model_scale * 1.00000} ${model_scale * 1.00000} '
        '${model_scale * 1.00000}"' in out
    )
    assert 'scale="1.00000 1.00000 1.00000"' not in out


def test_idempotent(mod):
    once = mod._transform(SAMPLE)
    twice = mod._transform(once)
    assert once == twice


@pytest.mark.skipif(not URDF_XACRO.is_file(), reason="robot_description.urdf.xacro missing")
def test_production_urdf_has_no_unscaled_meshes():
    """Every <mesh scale> in the production xacro must use ${model_scale}."""
    text = URDF_XACRO.read_text(encoding="utf-8")
    assert 'scale="1.00000 1.00000 1.00000"' not in text, (
        "Found <mesh scale=\"1 1 1\"/> in robot_description.urdf.xacro — run "
        "scripts/scale_xacro_origins.py to wrap mesh scale with ${model_scale}, "
        "otherwise joint frames shrink while DAEs stay full size."
    )


@pytest.mark.skipif(not URDF_XACRO.is_file(), reason="robot_description.urdf.xacro missing")
def test_production_urdf_has_no_raw_origin_xyz():
    """Every <origin xyz> in the production xacro must use ${model_scale}."""
    text = URDF_XACRO.read_text(encoding="utf-8")
    raw = re.findall(r'<origin\b[^>]*\sxyz="([^"]+)"', text)
    offenders = [
        v for v in raw
        if v.strip()
        and "model_scale" not in v
        and not all(part.strip() in {"0", "0.0"} for part in v.split())
    ]
    assert not offenders, f"Unscaled origin xyz values found: {offenders[:5]}"
