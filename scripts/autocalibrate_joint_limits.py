#!/usr/bin/env python3
# Copyright 2025 Sentience Robotics Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Auto-calibrate URDF joint limits via self-collision sweep (PyBullet).

For each actuated joint listed in config/hardware/active.yaml:
- Hold every other joint at zero (neutral pose).
- Step the joint upward in fine increments from 0 until self-collision.
- Step the joint downward similarly.
- Record the first-contact angle minus a safety margin.

What this CAN do
- Find the kinematic envelope of self-collision (chassis interference) for
  each joint independently from the chosen neutral pose.
- Skip adjacent-link pairs that overlap by construction (parent-child same
  origin) so they don't trigger spurious "always in contact" hits.

What this CANNOT do
- Find the actuator's mechanical end-stop (printed limit, gear stop, cable
  limit). Those need a real-world measurement or datasheet.
- Find the joint-space-wide reachable set (one-axis-at-a-time sweeps).
- Distinguish "barely touching mesh" from "real interference" — the bullet
  contact threshold is conservative; the script applies a 5° margin.

Usage
-----
    # pybullet ships with the lucy_ros2:humble image (Dockerfile: pip install pybullet);
    # host-side: pip install --user -r scripts/requirements.txt
    python3 scripts/autocalibrate_joint_limits.py                  # headless dry run
    python3 scripts/autocalibrate_joint_limits.py --apply          # write back
    python3 scripts/autocalibrate_joint_limits.py --step-deg 0.25 --margin-deg 3

Live visualization
------------------
- ``--view gui``: opens PyBullet's native GUI window. Zero ROS deps.
- ``--view rviz``: publishes ``/joint_states`` while sweeping. Watch the
  motion in your existing RViz config:

      ros2 launch thais_urdf joint_preview.launch.py jsp_gui:=false &
      python3 scripts/autocalibrate_joint_limits.py --view rviz --rate-hz 60

  The ``jsp_gui:=false`` flag turns off ``joint_state_publisher_gui`` so it
  doesn't fight the script for the topic.
- ``--joint <name>``: focus on a single joint (defaults to all actuated).
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
URDF_XACRO = ROOT / "description/urdf/inmoov.urdf.xacro"
BASE_PATH = ROOT / "description"
CONTROLLERS_YAML = ROOT / "config/controllers.yaml"
ACTIVE_YAML = ROOT / "config/hardware/active.yaml"
TARGET_XACRO = ROOT / "description/robot_description/urdf/robot_description.urdf.xacro"


@dataclass
class JointResult:
    name: str
    lower_rad: float
    upper_rad: float
    hit_lower: bool
    hit_upper: bool


def expand_urdf() -> str:
    if shutil.which("xacro"):
        cmd = ["xacro"]
    elif shutil.which("ros2"):
        cmd = ["ros2", "run", "xacro", "xacro"]
    else:
        sys.exit("xacro not on PATH (source ROS Humble)")
    cmd += [
        str(URDF_XACRO),
        f"base_path:={BASE_PATH}",
        f"controller_config:={CONTROLLERS_YAML}",
        "use_gazebo_sim:=false",
        "use_mock_hardware:=true",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        sys.exit(f"xacro failed:\n{r.stderr}")
    return r.stdout


def actuated_joints() -> list[str]:
    data = yaml.safe_load(ACTIVE_YAML.read_text(encoding="utf-8"))
    return [a["urdf_joint"] for a in data["actuators"]]


class Visualizer:
    """No-op viz hook (headless DIRECT mode)."""

    connection_mode_name = "DIRECT"

    def setup(self, p, body, name_to_idx, cid) -> None:  # noqa: D401 - protocol-ish
        return None

    def step(self, p, body, name_to_idx, cid) -> None:
        return None

    def teardown(self) -> None:
        return None


class PyBulletGuiVisualizer(Visualizer):
    """Open PyBullet's native GUI window — orbit camera, pause/resume, etc."""

    connection_mode_name = "GUI"

    def __init__(self, rate_hz: float):
        self._period = 1.0 / rate_hz if rate_hz > 0 else 0.0

    def setup(self, p, body, name_to_idx, cid) -> None:
        # Frame the robot: ~3 m back, slight pitch, focus near the chest.
        p.resetDebugVisualizerCamera(
            cameraDistance=2.5,
            cameraYaw=45,
            cameraPitch=-15,
            cameraTargetPosition=[0.0, 0.0, 1.0],
            physicsClientId=cid,
        )

    def step(self, p, body, name_to_idx, cid) -> None:
        # PyBullet's GUI updates on each setJointState; just pace it.
        if self._period:
            time.sleep(self._period)


class RvizVisualizer(Visualizer):
    """Publish ``/joint_states`` so an RViz already showing /robot_description renders the sweep."""

    connection_mode_name = "DIRECT"

    def __init__(self, rate_hz: float):
        self._period = 1.0 / rate_hz if rate_hz > 0 else 0.0
        self._node = None
        self._pub = None
        self._joint_names: list[str] = []
        self._JointState = None

    def setup(self, p, body, name_to_idx, cid) -> None:
        try:
            import rclpy
            from rclpy.node import Node
            from sensor_msgs.msg import JointState
        except ImportError:
            sys.exit(
                "[--view rviz] rclpy/sensor_msgs not importable. "
                "Source ROS Humble first (e.g. `source install/setup.bash`)."
            )
        if not rclpy.ok():
            rclpy.init()
        self._JointState = JointState
        self._node = Node("autocalibrate_joint_limits_viz")
        self._pub = self._node.create_publisher(JointState, "/joint_states", 10)
        # Only joints PyBullet considers articulated end up in name_to_idx — that
        # matches the URDF joint count, which is what robot_state_publisher expects.
        self._joint_names = list(name_to_idx.keys())
        self._idxs = [name_to_idx[n] for n in self._joint_names]
        print(
            f"[--view rviz] publishing /joint_states for {len(self._joint_names)} joints. "
            "Make sure `ros2 launch thais_urdf joint_preview.launch.py jsp_gui:=false` is running."
        )

    def step(self, p, body, name_to_idx, cid) -> None:
        if self._pub is None:
            return
        positions = [
            p.getJointState(body, j, physicsClientId=cid)[0] for j in self._idxs
        ]
        msg = self._JointState()
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.name = self._joint_names
        msg.position = positions
        self._pub.publish(msg)
        if self._period:
            time.sleep(self._period)

    def teardown(self) -> None:
        try:
            import rclpy

            if self._node is not None:
                self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


def _make_visualizer(view: str, rate_hz: float) -> Visualizer:
    if view == "gui":
        return PyBulletGuiVisualizer(rate_hz)
    if view == "rviz":
        return RvizVisualizer(rate_hz)
    return Visualizer()


def sweep(
    urdf_text: str,
    joint_names: list[str],
    step_deg: float,
    margin_deg: float,
    max_sweep_deg: float,
    visualizer: Optional[Visualizer] = None,
    penetration_mm: float = 1.0,
    log_baseline: bool = False,
) -> list[JointResult]:
    try:
        import pybullet as p
    except ImportError:
        sys.exit("pybullet not installed (pip install pybullet)")

    viz = visualizer or Visualizer()
    threshold = -abs(penetration_mm) * 1e-3  # bullet contactDistance is in metres, < 0 = penetration

    with tempfile.NamedTemporaryFile("w", suffix=".urdf", delete=False) as fh:
        fh.write(urdf_text)
        urdf_path = fh.name

    pb_mode = p.GUI if viz.connection_mode_name == "GUI" else p.DIRECT
    cid = p.connect(pb_mode)
    flags = p.URDF_USE_SELF_COLLISION | p.URDF_USE_SELF_COLLISION_EXCLUDE_PARENT
    body = p.loadURDF(urdf_path, useFixedBase=True, flags=flags, physicsClientId=cid)

    name_to_idx: dict[str, int] = {}
    for j in range(p.getNumJoints(body, physicsClientId=cid)):
        info = p.getJointInfo(body, j, physicsClientId=cid)
        joint_name = info[1].decode("utf-8")
        name_to_idx[joint_name] = j

    # Map link index -> link name for diagnostics; PyBullet link N corresponds
    # to joint N's child (linkName field in getJointInfo). Index -1 is the
    # base link.
    link_name = {-1: "<base>"}
    for j in range(p.getNumJoints(body, physicsClientId=cid)):
        info = p.getJointInfo(body, j, physicsClientId=cid)
        link_name[j] = info[12].decode("utf-8")

    viz.setup(p, body, name_to_idx, cid)

    def reset_neutral():
        for j in name_to_idx.values():
            p.resetJointState(body, j, 0.0, physicsClientId=cid)
        viz.step(p, body, name_to_idx, cid)

    def set_and_pulse(j_idx: int, angle: float) -> None:
        p.resetJointState(body, j_idx, angle, physicsClientId=cid)
        viz.step(p, body, name_to_idx, cid)

    def contact_pairs() -> set[tuple[int, int]]:
        """
        Return link pairs currently penetrating beyond the threshold.

        Indices are sorted so order doesn't matter; same-link contacts are
        ignored (PyBullet folds multi-mesh links into one rigid body, so this
        is effectively a no-op for the usual case).
        """
        p.performCollisionDetection(physicsClientId=cid)
        out: set[tuple[int, int]] = set()
        for c in p.getContactPoints(bodyA=body, bodyB=body, physicsClientId=cid):
            if c[8] >= threshold:
                continue
            a, b = c[3], c[4]
            if a == b:
                continue
            out.add((min(a, b), max(a, b)))
        return out

    # Capture the "always touching" pairs at neutral pose. Sub-meshes belonging
    # to adjacent links (torso z/y, shoulder/upper-arm, ...) are authored to
    # share material across the joint, so they count as overlapping but are
    # not real interferences. We mask them out for the rest of the run.
    reset_neutral()
    baseline = contact_pairs()
    if baseline:
        print(
            f"[baseline] {len(baseline)} link pair(s) overlap at neutral pose; "
            "ignoring them as authored mesh overlap."
        )
        if log_baseline:
            for a, b in sorted(baseline):
                print(f"  {link_name.get(a, f'#{a}')}  <->  {link_name.get(b, f'#{b}')}")

    def has_new_collision() -> bool:
        return bool(contact_pairs() - baseline)

    step_rad = math.radians(step_deg)
    max_sweep_rad = math.radians(max_sweep_deg)
    margin_rad = math.radians(margin_deg)
    results: list[JointResult] = []

    try:
        for name in joint_names:
            if name not in name_to_idx:
                print(f"[skip] {name} not in URDF")
                continue
            j_idx = name_to_idx[name]
            info = p.getJointInfo(body, j_idx, physicsClientId=cid)
            urdf_lower, urdf_upper = info[8], info[9]
            if urdf_lower >= urdf_upper:  # continuous joint, fall back to ±180°
                urdf_lower, urdf_upper = -math.pi, math.pi

            reset_neutral()
            # Even with the baseline mask there can be a residual new contact
            # at neutral right after re-resetting (e.g. rounding); treat that
            # as a hard skip with a clear message.
            if has_new_collision():
                print(f"[warn] {name}: new contact at neutral after reset; skipping")
                results.append(
                    JointResult(name, urdf_lower, urdf_upper, hit_lower=False, hit_upper=False)
                )
                continue

            print(f"[sweep] {name}")
            upper_hit = urdf_upper
            hit_u = False
            angle = 0.0
            while angle <= min(urdf_upper, max_sweep_rad):
                set_and_pulse(j_idx, angle)
                if has_new_collision():
                    upper_hit = max(0.0, angle - margin_rad)
                    hit_u = True
                    break
                angle += step_rad
            reset_neutral()

            lower_hit = urdf_lower
            hit_l = False
            angle = 0.0
            while angle >= max(urdf_lower, -max_sweep_rad):
                set_and_pulse(j_idx, angle)
                if has_new_collision():
                    lower_hit = min(0.0, angle + margin_rad)
                    hit_l = True
                    break
                angle -= step_rad
            reset_neutral()

            results.append(JointResult(name, lower_hit, upper_hit, hit_l, hit_u))
    finally:
        viz.teardown()
        p.disconnect(cid)
        Path(urdf_path).unlink(missing_ok=True)
    return results


JOINT_LIMIT_RE = re.compile(
    r'(<joint name="(?P<name>[^"]+)"[^>]*>\s*)'
    r'<limit\s+lower="[^"]*"\s+upper="[^"]*"\s+'
    r'(?P<rest>effort="[^"]*"\s+velocity="[^"]*")\s*/>'
    r'(\s*<!--[^>]*-->)?',
    re.DOTALL,
)


def apply_to_xacro(results: list[JointResult]) -> None:
    by_name = {r.name: r for r in results}
    text = TARGET_XACRO.read_text(encoding="utf-8")

    def repl(m: re.Match[str]) -> str:
        name = m.group("name")
        rest = m.group("rest")
        if name not in by_name:
            return m.group(0)
        r = by_name[name]
        deg_lo = math.degrees(r.lower_rad)
        deg_hi = math.degrees(r.upper_rad)
        comment = (
            f"<!-- autocalibrated: {deg_lo:.1f} deg .. {deg_hi:.1f} deg "
            f"(hit_lower={r.hit_lower}, hit_upper={r.hit_upper}) -->"
        )
        return (
            f'{m.group(1)}<limit lower="{r.lower_rad:.5f}" '
            f'upper="{r.upper_rad:.5f}" {rest}/>{comment}'
        )

    TARGET_XACRO.write_text(JOINT_LIMIT_RE.sub(repl, text), encoding="utf-8")
    print(f"Wrote autocalibrated limits to {TARGET_XACRO}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--step-deg", type=float, default=0.5)
    ap.add_argument("--margin-deg", type=float, default=5.0)
    ap.add_argument("--max-sweep-deg", type=float, default=180.0)
    ap.add_argument("--apply", action="store_true", help="Write results back into the xacro")
    ap.add_argument(
        "--view",
        choices=("none", "gui", "rviz"),
        default="none",
        help="none = headless (default); gui = PyBullet native window; "
        "rviz = publish /joint_states (requires `joint_preview.launch.py jsp_gui:=false`)",
    )
    ap.add_argument(
        "--rate-hz",
        type=float,
        default=0.0,
        help="Throttle the sweep so it's watchable. 0 = no throttle "
        "(default for --view none); for --view gui/rviz a default of 60 Hz "
        "is applied if you leave this at 0.",
    )
    ap.add_argument(
        "--joint",
        action="append",
        default=None,
        help="Restrict the sweep to a single actuated joint by URDF name. "
        "Can be passed multiple times. Useful with --view to demo one axis.",
    )
    ap.add_argument(
        "--penetration-mm",
        type=float,
        default=1.0,
        help="Contact-distance threshold below which a contact counts as a "
        "collision (in millimetres). Increase if the all-mesh URDF is noisy "
        "and reports spurious 0.x mm overlaps as new collisions.",
    )
    ap.add_argument(
        "--log-baseline",
        action="store_true",
        help="Print every link pair that overlaps at neutral pose. Useful to "
        "verify that 'authored mesh overlap' is what's being masked out, not "
        "a real bug in the URDF.",
    )
    args = ap.parse_args()

    rate_hz = args.rate_hz
    if rate_hz == 0.0 and args.view in ("gui", "rviz"):
        rate_hz = 60.0

    print("Expanding xacro...")
    urdf_text = expand_urdf()
    joints = actuated_joints()
    if args.joint:
        wanted = set(args.joint)
        unknown = wanted - set(joints)
        if unknown:
            sys.exit(f"--joint not in active.yaml actuators: {sorted(unknown)}")
        joints = [j for j in joints if j in wanted]
    viz = _make_visualizer(args.view, rate_hz)
    print(
        f"Sweeping {len(joints)} actuated joints "
        f"(step={args.step_deg}°, view={args.view}, rate_hz={rate_hz or 'unbounded'})..."
    )
    results = sweep(
        urdf_text,
        joints,
        step_deg=args.step_deg,
        margin_deg=args.margin_deg,
        max_sweep_deg=args.max_sweep_deg,
        visualizer=viz,
        penetration_mm=args.penetration_mm,
        log_baseline=args.log_baseline,
    )
    print(f"\n{'joint':40s}  {'lower deg':>10s}  {'upper deg':>10s}  hit")
    print("-" * 80)
    for r in results:
        marker = (
            "<-> ok"
            if r.hit_lower and r.hit_upper
            else ("> upper" if r.hit_upper else ("< lower" if r.hit_lower else "free"))
        )
        print(
            f"{r.name:40s}  {math.degrees(r.lower_rad):10.2f}  "
            f"{math.degrees(r.upper_rad):10.2f}  {marker}"
        )
    if args.apply:
        apply_to_xacro(results)
    else:
        print("\nDry run. Pass --apply to write results into the xacro.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
