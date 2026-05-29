# Copyright 2025 Sentience Robotics Team
# SPDX-License-Identifier: GPL-3.0-or-later

"""All-mesh collision model: every link with a visual mesh has a mesh collision."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from xacro_helper import run_xacro

# Body links (Gazebo: self_collide=false).
BODY_LINKS = [
    "torso_bottom_link",
    "torso_z_link",
    "torso_y_link",
    "left_shoulder_y_link",
    "left_shoulder_x_link",
    "left_shoulder_z_link",
    "left_elbow_x_link",
    "left_wrist_z_link",
    "right_shoulder_y_link",
    "right_shoulder_x_link",
    "right_shoulder_z_link",
    "right_elbow_x_link",
    "right_wrist_z_link",
    "neck_link",
    "i01.head.rothead_link",
    "i01.head.jaw_link",
]

# Hand links (Gazebo: self_collide=true, high mu).
_HAND_LINK_BASES = [
    "wrist.001",
    "index", "index2", "index3",
    "majeure", "majeure2", "majeure3",
    "ringfinger0", "ringFinger", "ringfinger2", "ringfinger3",
    "pinky0", "pinky", "pinky2", "pinky3",
    "thumb1", "thumb", "thumb3",
]
HAND_LINKS = [
    f"i01.{side}Hand.{base}_link"
    for side in ("left", "right")
    for base in _HAND_LINK_BASES
]


def _expand_urdf() -> ET.Element:
    root = Path(__file__).resolve().parents[1]
    r = run_xacro(
        [
            str(root / "description/urdf/inmoov.urdf.xacro"),
            f"base_path:={root / 'description'}",
            f"controller_config:={root / 'config/controllers.yaml'}",
            "use_gazebo_sim:=false",
            "use_mock_hardware:=true",
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    return ET.fromstring(r.stdout)


@pytest.fixture(scope="module")
def urdf_root():
    return _expand_urdf()


def _link_collisions(urdf_root: ET.Element, link_name: str) -> list[ET.Element]:
    for link in urdf_root.findall("link"):
        if link.get("name") == link_name:
            return link.findall("collision")
    return []


def test_body_mesh_collisions(urdf_root):
    """Body links must use mesh-reuse collisions (no primitive boxes/cylinders)."""
    for name in BODY_LINKS:
        cols = _link_collisions(urdf_root, name)
        assert cols, f"{name} missing collision"
        mesh = cols[0].find(".//mesh")
        assert mesh is not None, f"{name} should reuse visual mesh for collision"
        # Reject any primitive geometry under this collision.
        for prim in ("box", "cylinder", "sphere"):
            assert cols[0].find(f".//{prim}") is None, (
                f"{name} should not use primitive <{prim}> collision"
            )


def test_hand_mesh_collisions(urdf_root):
    """Every phalanx + palm link reuses its visual mesh as collision."""
    for name in HAND_LINKS:
        cols = _link_collisions(urdf_root, name)
        assert cols, f"{name} missing collision"
        mesh = cols[0].find(".//mesh")
        assert mesh is not None, f"{name} should reuse visual mesh for collision"


def test_all_visual_links_have_collision(urdf_root):
    """Any link with a <visual><mesh/> must have at least one <collision>.

    Eye-pivot frames (eyeRight.001, eyeLeft.001, neck.001) are intermediate
    transforms with no visual — they may legitimately have no collision.
    """
    missing: list[str] = []
    for link in urdf_root.findall("link"):
        name = link.get("name") or ""
        has_visual_mesh = any(
            v.find(".//mesh") is not None for v in link.findall("visual")
        )
        has_collision = link.find("collision") is not None
        if has_visual_mesh and not has_collision:
            missing.append(name)
    assert not missing, f"links with visual mesh but no collision: {missing}"


def test_every_visual_mesh_has_paired_collision(urdf_root):
    """Per-visual coverage: links with N visual meshes get N (or more) collisions.

    Multi-mesh links like ``torso_y_link`` (80 sub-DAEs) must collide as the
    full visual hull, not just a single representative mesh. Hand-authored
    primitive collisions on ``base_node`` / ``stand_link`` are allowed extras.
    """
    short: list[str] = []
    for link in urdf_root.findall("link"):
        name = link.get("name") or ""
        n_visual_mesh = sum(
            1 for v in link.findall("visual") if v.find(".//mesh") is not None
        )
        n_collision_mesh = sum(
            1 for c in link.findall("collision") if c.find(".//mesh") is not None
        )
        if n_visual_mesh and n_collision_mesh < n_visual_mesh:
            short.append(f"{name}: {n_visual_mesh} visuals, {n_collision_mesh} collisions")
    assert not short, "links with fewer mesh collisions than visuals: " + ", ".join(short)
