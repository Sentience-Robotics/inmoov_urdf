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

"""Structural validation for config/hardware/active.yaml (issue #95)."""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
import yaml

REQUIRED_ROOT = (
    "version",
    "robot_name",
    "firmware",
    "controller_manager",
    "boards",
    "actuators",
    "sensors",
)
REQUIRED_ACTUATOR = (
    "id",
    "urdf_joint",
    "board",
    "virtual_pin",
    "physical_pin",
    "servo_type",
    "offset_deg",
    "direction",
    "scale",
    "servo_min_deg",
    "servo_max_deg",
    "servo_default_deg",
    "enabled",
)
REQUIRED_SENSOR = (
    "id",
    "type",
    "associated_actuator",
    "board",
    "virtual_pin",
    "physical_pin",
    "min_value",
    "max_value",
    "enabled",
)
REQUIRED_BOARD = (
    "serial_id",
    "board_class",
    "internal_servo_slots",
    "firmware_target",
    "compile_definition",
    "topic_actuators",
    "topic_sensors",
    "controller",
)

BOARD_CLASSES = frozenset({"internal_servo_only", "internal_servo_i2c_pwm"})
_BOARD_ID_RE = re.compile(r"^rp2040_[a-z][a-z0-9_]*$")
_TOPIC_RE = re.compile(r"^[a-z][a-z0-9_/]*$")
_SERIAL_ID_RE = re.compile(r"^[A-Za-z0-9]*$")


def _active_yaml_path() -> Path:
    """Prefer the checkout under ``test/..`` so pytest validates edited YAML without reinstall."""
    src = Path(__file__).resolve().parents[1] / "config" / "hardware" / "active.yaml"
    if src.is_file():
        return src
    try:
        from ament_index_python.packages import get_package_share_directory

        p = Path(get_package_share_directory("inmoov_urdf")) / "config" / "hardware" / "active.yaml"
        if p.is_file():
            return p
    except Exception:
        pass
    return src


def _urdf_xacro_path() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("inmoov_urdf"))
        urdf = share / "description" / "urdf" / "inmoov.urdf.xacro"
        if urdf.is_file():
            return urdf
    except Exception:
        pass
    root = Path(__file__).resolve().parents[1]
    return root / "description" / "urdf" / "inmoov.urdf.xacro"


def _controllers_yaml_path() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory

        p = Path(get_package_share_directory("inmoov_urdf")) / "config" / "controllers.yaml"
        if p.is_file():
            return p
    except Exception:
        pass
    return Path(__file__).resolve().parents[1] / "config" / "controllers.yaml"


def load_hardware_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_hardware_yaml(data: dict[str, Any], urdf_joints: set[str] | None = None) -> None:
    for key in REQUIRED_ROOT:
        if key not in data:
            raise ValueError(f"missing root key: {key}")
    if data["version"] != 1:
        raise ValueError("version must be 1")
    boards: dict[str, Any] = data["boards"]
    if not isinstance(boards, dict) or not boards:
        raise ValueError("boards must be a non-empty map")

    for bid, bdef in boards.items():
        for k in REQUIRED_BOARD:
            if k not in bdef:
                raise ValueError(f"board {bid}: missing {k}")
        ctrl = bdef["controller"]
        if "name" not in ctrl or "type" not in ctrl:
            raise ValueError(f"board {bid}: controller needs name and type")

        if not _BOARD_ID_RE.fullmatch(bid):
            raise ValueError(
                f"board id {bid!r} must match {_BOARD_ID_RE.pattern} "
                "(must stay aligned with lucy_config_generator derivation rules)"
            )
        bc = bdef["board_class"]
        if bc not in BOARD_CLASSES:
            raise ValueError(
                f"board {bid}: board_class must be one of {sorted(BOARD_CLASSES)}, got {bc!r}"
            )
        sid = bdef["serial_id"]
        if not isinstance(sid, str):
            raise ValueError(f"board {bid}: serial_id must be a string")
        if sid and not _SERIAL_ID_RE.fullmatch(sid):
            raise ValueError(
                f"board {bid}: serial_id must be empty or alphanumeric "
                "(USB serial / picotool --ser)"
            )
        for topic_key in ("topic_actuators", "topic_sensors"):
            t = bdef[topic_key]
            if not isinstance(t, str) or not t:
                raise ValueError(f"board {bid}: {topic_key} must be a non-empty string")
            if not _TOPIC_RE.fullmatch(t):
                raise ValueError(
                    f"board {bid}: {topic_key} must match {_TOPIC_RE.pattern} (no leading slash)"
                )

    actuators: list[dict[str, Any]] = data["actuators"]
    if not isinstance(actuators, list):
        raise ValueError("actuators must be a list")
    by_board: dict[str, list[dict[str, Any]]] = {}
    for a in actuators:
        for k in REQUIRED_ACTUATOR:
            if k not in a:
                raise ValueError(f"actuator {a.get('id')}: missing {k}")
        b = a["board"]
        if b not in boards:
            raise ValueError(f"actuator {a['id']}: unknown board {b}")
        by_board.setdefault(b, []).append(a)

    for board_id, lst in by_board.items():
        vpins = sorted(int(x["virtual_pin"]) for x in lst)
        if len(vpins) != len(set(vpins)):
            raise ValueError(f"board {board_id}: duplicate virtual_pin")
        if vpins != list(range(len(vpins))):
            raise ValueError(
                f"board {board_id}: virtual_pin must be contiguous from 0..N-1, got {vpins}"
            )
        for a in lst:
            lo = a["servo_min_deg"]
            hi = a["servo_max_deg"]
            d = a["servo_default_deg"]
            if lo is not None and hi is not None and d is not None:
                if float(d) < float(lo) or float(d) > float(hi):
                    raise ValueError(
                        f"actuator {a['id']}: servo_default_deg out of [{lo}, {hi}]"
                    )

    sensors: list[dict[str, Any]] = data["sensors"]
    if not isinstance(sensors, list):
        raise ValueError("sensors must be a list")
    actuator_ids = {a["id"] for a in actuators}
    for s in sensors:
        for k in REQUIRED_SENSOR:
            if k not in s:
                raise ValueError(f"sensor {s.get('id')}: missing {k}")
        if s["board"] not in boards:
            raise ValueError(f"sensor {s['id']}: unknown board {s['board']}")
        if s["associated_actuator"] not in actuator_ids:
            raise ValueError(
                f"sensor {s['id']}: associated_actuator {s['associated_actuator']} not found"
            )

    if urdf_joints is not None:
        for a in actuators:
            j = a["urdf_joint"]
            if j not in urdf_joints:
                raise ValueError(f"actuator {a['id']}: urdf_joint {j!r} not in URDF")


def urdf_joint_names_from_xacro() -> set[str]:
    xacro = shutil.which("xacro")
    if not xacro:
        pytest.skip("xacro not on PATH")
    urdf = _urdf_xacro_path()
    ctrl = _controllers_yaml_path()
    if not urdf.is_file():
        pytest.skip(f"missing {urdf}")
    if not ctrl.is_file():
        pytest.skip(f"missing {ctrl}")
    base = urdf.parent.parent
    cmd = [
        xacro,
        str(urdf),
        f"base_path:={base}",
        f"controller_config:={ctrl}",
        "use_gazebo_sim:=false",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if r.returncode != 0:
        pytest.skip(f"xacro failed: {r.stderr}")
    root = ET.fromstring(r.stdout)
    return {j.attrib["name"] for j in root.findall("joint") if "name" in j.attrib}


def test_active_yaml_validates():
    path = _active_yaml_path()
    assert path.is_file(), f"missing {path}"
    data = load_hardware_yaml(path)
    validate_hardware_yaml(data, urdf_joint_names_from_xacro())


@pytest.mark.parametrize(
    "name,msg",
    [
        ("invalid_duplicate_vpin.yaml", "duplicate virtual_pin"),
        ("invalid_missing_board.yaml", "unknown board"),
        ("invalid_servo_default_out_of_range.yaml", "servo_default_deg"),
    ],
)
def test_invalid_fixture_rejected(name: str, msg: str):
    path = Path(__file__).resolve().parent / "fixtures" / name
    data = load_hardware_yaml(path)
    with pytest.raises(ValueError, match=msg):
        validate_hardware_yaml(data)
