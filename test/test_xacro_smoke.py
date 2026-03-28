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

"""Generate URDF with xacro (no Gazebo / ROS nodes). Uses install share when available."""
import shutil
import subprocess
from pathlib import Path

import pytest


def _inmoov_paths():
    try:
        from ament_index_python.packages import get_package_share_directory
        share = Path(get_package_share_directory("thais_urdf"))
        inmoov = share / "inmoov"
        urdf = inmoov / "urdf" / "inmoov.urdf.xacro"
        if urdf.is_file():
            return urdf, inmoov
    except Exception:
        pass
    root = Path(__file__).resolve().parents[1]
    inmoov = root / "inmoov"
    urdf = inmoov / "urdf" / "inmoov.urdf.xacro"
    return urdf, inmoov


def _controller_yaml() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory
        p = (
            Path(get_package_share_directory("lucy_ros2_control"))
            / "config"
            / "lucy_controllers.yaml"
        )
        if p.is_file():
            return p
    except Exception:
        pass
    ws_src = Path(__file__).resolve().parents[1].parent
    return ws_src / "lucy_ros2_control" / "config" / "lucy_controllers.yaml"


@pytest.fixture(scope="module")
def controller_config() -> Path:
    path = _controller_yaml()
    if not path.is_file():
        pytest.skip(
            "Missing lucy_ros2_control/config/lucy_controllers.yaml — "
            "build lucy_ros2_control or place it next to thais_urdf under colcon src/"
        )
    return path


def test_xacro_real_mode(controller_config: Path):
    xacro = shutil.which("xacro")
    assert xacro, "xacro not on PATH (install ros-humble-xacro)"
    urdf, base = _inmoov_paths()
    assert urdf.is_file(), f"missing {urdf} — colcon build thais_urdf to install inmoov/"
    cmd = [
        xacro,
        str(urdf),
        f"base_path:={base}",
        f"controller_config:={controller_config}",
        "use_gazebo_sim:=false",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "<robot" in r.stdout


def test_xacro_gazebo_mode(controller_config: Path):
    xacro = shutil.which("xacro")
    assert xacro, "xacro not on PATH (install ros-humble-xacro)"
    urdf, base = _inmoov_paths()
    assert urdf.is_file(), f"missing {urdf} — colcon build thais_urdf to install inmoov/"
    cmd = [
        xacro,
        str(urdf),
        f"base_path:={base}",
        f"controller_config:={controller_config}",
        "use_gazebo_sim:=true",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "<robot" in r.stdout
