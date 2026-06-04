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

# Real robot / RViz-only: lucy_control_supervisor owns RSP + ros2_control_node + spawners.

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import yaml


_DEFAULT_GENERATED_FILES = {
    "ros2_control_xacro": "inmoov_ros2_control.xacro",
    "controllers_yaml": "controllers.yaml",
}


def _load_launch_defaults(package_root: Path) -> dict[str, str]:
    config_path = package_root / "config" / "control.launch.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid launch defaults file: {config_path}")
    required = ("urdf_path", "base_path", "controllers_yaml")
    missing = [key for key in required if key not in data or not str(data[key]).strip()]
    if missing:
        raise RuntimeError(f"Missing keys in {config_path}: {missing}")
    return {key: str(data[key]).strip() for key in required}


def _active_generated_files(package_root: Path) -> dict[str, str]:
    """Generated-artifact filenames from the active preset (defaults if unreadable)."""
    active = package_root / "config" / "hardware" / "active.yaml"
    out = dict(_DEFAULT_GENERATED_FILES)
    try:
        data = yaml.safe_load(active.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return out
    section = data.get("generated_files") if isinstance(data, dict) else None
    if isinstance(section, dict):
        for key in out:
            value = section.get(key)
            if isinstance(value, str) and value.strip() and "/" not in value:
                out[key] = value.strip()
    return out


def generate_launch_description():
    package_root = Path(__file__).resolve().parents[1]
    defaults = _load_launch_defaults(package_root)
    generated = _active_generated_files(package_root)
    default_controllers_yaml = str(
        (package_root / "config" / generated["controllers_yaml"]).resolve()
    )
    default_urdf = str((package_root / defaults["urdf_path"]).resolve())
    default_base = str((package_root / defaults["base_path"]).resolve())

    try:
        supervisor_share = get_package_share_directory("lucy_control_supervisor")
    except Exception as e:
        raise RuntimeError(
            "lucy_control_supervisor package required for control.launch.py"
        ) from e

    controllers_yaml_arg = DeclareLaunchArgument(
        "controllers_yaml",
        default_value=default_controllers_yaml,
        description="Absolute path to controller_manager YAML config",
    )
    urdf_path_arg = DeclareLaunchArgument(
        "urdf_path",
        default_value=default_urdf,
        description="Top-level robot xacro path",
    )
    base_path_arg = DeclareLaunchArgument(
        "base_path",
        default_value=default_base,
        description="Base path for xacro mesh_dir",
    )
    use_mock_hardware_arg = DeclareLaunchArgument(
        "use_mock_hardware",
        default_value="false",
        description=(
            "Forwarded to xacro: LucySystemHardware with publish_actuators:=false "
            "(URDF clamping still applied, no micro-ROS publish)"
        ),
    )
    ros2_control_file_arg = DeclareLaunchArgument(
        "ros2_control_file",
        default_value=generated["ros2_control_xacro"],
        description="Generated ros2_control xacro basename (generated_files in active.yaml)",
    )

    supervisor_launch = TimerAction(
        period=2.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [supervisor_share, "/launch/control_supervisor.launch.py"]
                ),
                launch_arguments={
                    "urdf_path": LaunchConfiguration("urdf_path"),
                    "base_path": LaunchConfiguration("base_path"),
                    "controllers_yaml": LaunchConfiguration("controllers_yaml"),
                    "use_gazebo_sim": "false",
                    "use_mock_hardware": LaunchConfiguration("use_mock_hardware"),
                    "gazebo_only": "false",
                    "autostart": "true",
                    "ros2_control_file": LaunchConfiguration("ros2_control_file"),
                }.items(),
            )
        ],
    )

    return LaunchDescription(
        [
            controllers_yaml_arg,
            urdf_path_arg,
            base_path_arg,
            use_mock_hardware_arg,
            ros2_control_file_arg,
            supervisor_launch,
        ]
    )
