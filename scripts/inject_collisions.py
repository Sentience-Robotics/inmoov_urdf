#!/usr/bin/env python3
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
"""
Inject mesh-reuse collision blocks for every visual mesh in every link.

Strategy
--------
For each `<link name="...">` in the URDF:
- Iterate over every `<visual name="X">` that contains a `<mesh filename="..."/>`.
- For each, emit a paired `<collision name="X_collision">` reusing the visual's
  <origin> and <mesh filename> with a uniform ${model_scale} mesh scale (matches
  scale_xacro_origins.py output). What you see in RViz is what PyBullet/Gazebo
  collide against — including every sub-mesh of multi-mesh body links like
  `torso_y_link` (80+ DAEs glued together).
- Skip a visual if `name="<visual_name>_collision"` already exists in the same
  link (idempotent on re-runs).
- Skip pre-existing hand-authored collisions (e.g. `base_node_collision` 1 cm
  box) by name match — they coexist with the per-visual mesh collisions.
- Replace any placeholder inertial (mass=0.001) with a more reasonable
  mass=0.15 / 0.001 inertia tensor so dynamic sims do not blow up on
  near-massless bodies.

Note: this produces one collision per sub-mesh — Lucy ends up with ~290
collisions. For PyBullet auto-cal this is fine; for Gazebo dynamic contact-rich
work consider convex-decomposing or merging meshes (V-HACD).

Idempotent: re-running the script after edits is a no-op unless visuals were
added or collisions were removed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Named groups only — avoids off-by-one when nested inside numbered ().
LINK_BLOCK = re.compile(
    r'<link name="(?P<name>[^"]+)">(?P<body>.*?)(?P<close>\n  </link>)',
    re.DOTALL,
)

# Each <visual name="..."> ... </visual> block that contains a mesh filename.
VISUAL_BLOCK = re.compile(
    r'<visual\s+name="(?P<vname>[^"]+)"[^>]*>'
    r'(?P<inside>(?:(?!</visual>).)*?'
    r'<origin(?P<origin>[^/]*)/>'
    r'(?:(?!</visual>).)*?'
    r'<geometry>\s*<mesh\s+filename="(?P<mesh>[^"]+)"[^/]*/>\s*</geometry>'
    r'(?:(?!</visual>).)*?)</visual>',
    re.DOTALL,
)

PLACEHOLDER_INERTIAL = (
    '<inertial><mass value="0.001"/>'
    '<inertia ixx="1e-6" ixy="0" ixz="0" iyy="1e-6" iyz="0" izz="1e-6"/></inertial>'
)
BETTER_INERTIAL = (
    '<inertial><mass value="0.15"/>'
    '<inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.001"/></inertial>'
)

# Mesh scale matches scale_xacro_origins.py output for consistency.
_MESH_SCALE = "${model_scale * 1.00000} ${model_scale * 1.00000} ${model_scale * 1.00000}"

# Sanity-check token: catches "<originrpy=" if a future edit drops the space.
MALFORMED_ORIGIN = re.compile(r"<origin[a-z]")


# Body / hand classification only used for exporting the link sets that the
# Gazebo xacro and tests consume. Both groups now use mesh-reuse collisions;
# the split exists purely for Gazebo physics properties (friction, kp/kd,
# self_collide). Keep aligned with description/gazebo/inmoov_gazebo_physics.xacro.
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


def _collision_for_visual(visual_name: str, origin_attrs: str, mesh_file: str) -> str:
    """Emit a <collision name="<visual>_collision"> reusing one visual's mesh."""
    # Keep a leading space so we render "<origin rpy=..."> not "<originrpy=...>".
    origin = " " + origin_attrs.strip()
    return (
        f'\n    <collision name="{visual_name}_collision">'
        f'\n      <origin{origin}/>'
        f'\n      <geometry>'
        f'\n        <mesh filename="{mesh_file}" scale="{_MESH_SCALE}"/>'
        f'\n      </geometry>'
        f'\n    </collision>'
    )


def _inject_link(_name: str, body: str) -> str:
    """
    For each visual mesh in this link, append a paired collision.

    Collision names are derived from the visual's `name=` attribute, so the
    operation is idempotent on re-runs.
    """
    snippets: list[str] = []
    for m in VISUAL_BLOCK.finditer(body):
        vname = m.group("vname")
        cname = f'{vname}_collision'
        if f'name="{cname}"' in body:
            continue
        snippets.append(_collision_for_visual(vname, m.group("origin"), m.group("mesh")))
    if not snippets:
        return body
    body = body.replace(PLACEHOLDER_INERTIAL, BETTER_INERTIAL, 1)
    return "".join(snippets) + "\n" + body


def validate_urdf_fragment(text: str) -> None:
    """Raise ValueError if link tags or collision origins look broken."""
    opens = len(re.findall(r"<link\s+name=", text))
    closes = text.count("</link>")
    if opens != closes:
        raise ValueError(f"link tag mismatch: {opens} opens vs {closes} closes")
    if MALFORMED_ORIGIN.search(text):
        raise ValueError("malformed <origin> tag (missing space before rpy/xyz)")


def transform(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        name = m.group("name")
        new_body = _inject_link(name, m.group("body"))
        return f'<link name="{name}">{new_body}{m.group("close")}'

    if not LINK_BLOCK.search(text):
        raise ValueError("no <link> blocks matched (expected '\\n  </link>' closers)")
    updated = LINK_BLOCK.sub(repl, text)
    validate_urdf_fragment(updated)
    return updated


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "")
    if not path.is_file():
        print(f"Usage: {sys.argv[0]} robot_description.urdf.xacro", file=sys.stderr)
        return 1
    original = path.read_text(encoding="utf-8")
    try:
        updated = transform(original)
    except ValueError as exc:
        print(f"inject_collisions: {exc}", file=sys.stderr)
        return 1
    if updated == original:
        print("No collision changes.")
        return 0
    path.write_text(updated, encoding="utf-8")
    print(f"Injected mesh collisions into {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
