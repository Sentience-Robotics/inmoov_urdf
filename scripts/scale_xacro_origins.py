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
"""Wrap origin xyz, primitive sizes, and mesh scale with ${model_scale * N}."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ORIGIN_XYZ = re.compile(
    r'(<origin\b[^>]*\sxyz=")([^"]+)(")',
    re.MULTILINE,
)
BOX_SIZE = re.compile(
    r'(<box\s+size=")([^"]+)(")',
    re.MULTILINE,
)
CYLINDER = re.compile(
    r'(<cylinder\s+length=")([^"]+)("\s+radius=")([^"]+)(")',
    re.MULTILINE,
)
SPHERE_RADIUS = re.compile(
    r'(<sphere\s+radius=")([^"]+)(")',
    re.MULTILINE,
)
# Mesh <mesh filename="..." scale="x y z"/>. Without scaling the mesh, only
# joint origins shrink while geometry stays at full CAD size, which makes the
# stand and torso visibly misalign.
MESH_SCALE = re.compile(
    r'(<mesh\s+filename="[^"]+"\s+scale=")([^"]+)(")',
    re.MULTILINE,
)


def _scale_token(value: str) -> str:
    value = value.strip()
    if not value or "model_scale" in value or "${" in value:
        return value
    return f"${{model_scale * {value}}}"


def _scale_triple(triple: str) -> str:
    parts = triple.split()
    if len(parts) != 3:
        return triple
    return " ".join(_scale_token(p) for p in parts)


def _transform(text: str) -> str:
    text = ORIGIN_XYZ.sub(
        lambda m: f'{m.group(1)}{_scale_triple(m.group(2))}{m.group(3)}',
        text,
    )
    text = BOX_SIZE.sub(
        lambda m: f'{m.group(1)}{_scale_triple(m.group(2))}{m.group(3)}',
        text,
    )
    text = CYLINDER.sub(
        lambda m: (
            f'{m.group(1)}{_scale_token(m.group(2))}{m.group(3)}'
            f'{_scale_token(m.group(4))}{m.group(5)}'
        ),
        text,
    )
    text = SPHERE_RADIUS.sub(
        lambda m: f'{m.group(1)}{_scale_token(m.group(2))}{m.group(3)}',
        text,
    )
    text = MESH_SCALE.sub(
        lambda m: f'{m.group(1)}{_scale_triple(m.group(2))}{m.group(3)}',
        text,
    )
    return text


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "")
    if not path.is_file():
        print(f"Usage: {sys.argv[0]} robot_description.urdf.xacro", file=sys.stderr)
        return 1
    original = path.read_text(encoding="utf-8")
    updated = _transform(original)
    if updated == original:
        print("No changes (already scaled or no matches).")
        return 0
    path.write_text(updated, encoding="utf-8")
    print(f"Updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
