# Copyright 2025 Sentience Robotics Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Unit tests for scripts/inject_collisions.py."""

from __future__ import annotations

import importlib.util
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
URDF_XACRO = ROOT / "description/robot_description/urdf/robot_description.urdf.xacro"


def _load_inject_module():
    path = SCRIPTS / "inject_collisions.py"
    spec = importlib.util.spec_from_file_location("inject_collisions", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["inject_collisions"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def inj():
    return _load_inject_module()


_PLACEHOLDER_INERTIAL = """\
    <inertial>
      <mass value="0.001"/>
      <inertia ixx="1e-6" ixy="0" ixz="0" iyy="1e-6" iyz="0" izz="1e-6"/>
    </inertial>"""

SAMPLE_URDF = f"""\
<?xml version="1.0"?>
<robot name="test">
  <link name="frame_only">
{_PLACEHOLDER_INERTIAL}
  </link>
  <link name="torso_bottom_link">
    <visual name="torso_v">
      <origin rpy="0 0 0" xyz="0.0 0.0 1.0"/>
      <geometry>
        <mesh filename="${{mesh_dir}}/torso.dae" scale="1 1 1"/>
      </geometry>
    </visual>
{_PLACEHOLDER_INERTIAL}
  </link>
  <link name="i01.leftHand.index_link">
    <visual name="finger">
      <origin rpy="1.0 0.0 0.0" xyz="0.1 0.2 0.3"/>
      <geometry>
        <mesh filename="${{mesh_dir}}/finger.dae" scale="1 1 1"/>
      </geometry>
    </visual>
{_PLACEHOLDER_INERTIAL}
  </link>
  <link name="already_has_collision">
    <visual name="v">
      <origin rpy="0 0 0" xyz="0 0 0"/>
      <geometry><mesh filename="m.dae" scale="1 1 1"/></geometry>
    </visual>
    <collision name="hand_authored">
      <geometry><box size="0.01 0.01 0.01"/></geometry>
    </collision>
{_PLACEHOLDER_INERTIAL}
  </link>
</robot>
"""


def test_transform_preserves_link_closers(inj):
    out = inj.transform(SAMPLE_URDF)
    assert out.count("<link") == 4
    assert out.count("</link>") == 4
    inj.validate_urdf_fragment(out)


def test_mesh_collision_origin_has_space(inj):
    """Regression: '<originrpy=...' (no space) was emitted in an earlier version."""
    out = inj.transform(SAMPLE_URDF)
    assert '<origin rpy="1.0' in out
    assert "<originr" not in out


def test_body_link_gets_mesh_collision(inj):
    """Body links (torso, shoulders, ...) reuse the visual mesh as collision."""
    out = inj.transform(SAMPLE_URDF)
    # Per-visual collision name: '<visual_name>_collision'.
    assert 'name="torso_v_collision"' in out
    assert "torso.dae" in out
    # No primitive geometry should be injected — meshes only.
    assert "<box" not in out.split("torso_bottom_link")[1].split("</link>")[0]


def test_hand_link_gets_mesh_collision(inj):
    out = inj.transform(SAMPLE_URDF)
    assert 'name="finger_collision"' in out
    assert "finger.dae" in out


def test_skips_link_without_visual(inj):
    """Pure transform frames have no visual mesh — skip silently."""
    out = inj.transform(SAMPLE_URDF)
    frame_block = out.split('<link name="frame_only">')[1].split("</link>")[0]
    assert "<collision" not in frame_block


def test_preserves_existing_collision(inj):
    """
    Hand-authored collisions on base_node/stand_link must not be clobbered.

    The per-visual collision is still added alongside (the hand-authored block
    is named differently, so they don't conflict).
    """
    out = inj.transform(SAMPLE_URDF)
    block = out.split('<link name="already_has_collision">')[1].split("</link>")[0]
    assert 'name="hand_authored"' in block
    # Per-visual collision still gets injected (different name, no clash).
    assert 'name="v_collision"' in block


def test_inertial_upgraded_when_collision_added(inj):
    """Placeholder inertia (mass=0.001) is replaced once a collision is added."""
    out = inj.transform(SAMPLE_URDF)
    torso = out.split('<link name="torso_bottom_link">')[1].split("</link>")[0]
    assert 'mass value="0.15"' in torso


def test_idempotent_second_run(inj, tmp_path):
    path = tmp_path / "sample.urdf.xacro"
    path.write_text(SAMPLE_URDF, encoding="utf-8")
    first = inj.transform(path.read_text(encoding="utf-8"))
    path.write_text(first, encoding="utf-8")
    second = inj.transform(path.read_text(encoding="utf-8"))
    assert first == second


def test_main_noop_on_already_injected(inj, tmp_path, capsys):
    path = tmp_path / "sample.urdf.xacro"
    path.write_text(inj.transform(SAMPLE_URDF), encoding="utf-8")
    argv = sys.argv
    try:
        sys.argv = ["inject_collisions.py", str(path)]
        assert inj.main() == 0
        assert "No collision changes" in capsys.readouterr().out
    finally:
        sys.argv = argv


@pytest.mark.skipif(not URDF_XACRO.is_file(), reason="robot_description.urdf.xacro missing")
def test_production_urdf_balanced_links(inj):
    text = URDF_XACRO.read_text(encoding="utf-8")
    opens = len(re.findall(r"<link\s+name=", text))
    closes = text.count("</link>")
    assert opens == closes, f"{opens} link opens vs {closes} closes"
    assert not inj.MALFORMED_ORIGIN.search(text)


@pytest.mark.skipif(not URDF_XACRO.is_file(), reason="robot_description.urdf.xacro missing")
def test_production_urdf_xacro_expands(inj):
    """Expanded URDF must be well-formed XML (properties.xacro supplies model_scale)."""
    import shutil

    from xacro_helper import run_xacro

    if not shutil.which("xacro") and not shutil.which("ros2"):
        pytest.skip("xacro not on PATH")

    urdf = ROOT / "description/urdf/inmoov.urdf.xacro"
    r = run_xacro(
        [
            str(urdf),
            f"base_path:={ROOT / 'description'}",
            f"controller_config:={ROOT / 'config/controllers.yaml'}",
            "use_gazebo_sim:=false",
            "use_mock_hardware:=true",
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "${model_scale" not in r.stdout
    ET.fromstring(r.stdout)
