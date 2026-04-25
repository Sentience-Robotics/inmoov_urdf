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

# Real robot: robot_state_publisher + ros2_control_node + spawners.
# Controllers live in this package (config/controllers.yaml).

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
import yaml


def _controllers_to_spawn(controllers_yaml_path: Path) -> list[str]:
    """Return controller names declared under controller_manager.ros__parameters."""
    data = yaml.safe_load(controllers_yaml_path.read_text(encoding="utf-8")) or {}
    cm_params = data.get("controller_manager", {}).get("ros__parameters", {})
    if not isinstance(cm_params, dict):
        return []
    return [name for name in cm_params.keys() if name != "update_rate"]


def _load_launch_defaults(package_root: Path) -> dict[str, str]:
    """Load launch path defaults from config/control.launch.yaml."""
    config_path = package_root / "config" / "control.launch.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid launch defaults file: {config_path}")
    required = ("urdf_path", "base_path", "controllers_yaml")
    missing = [key for key in required if key not in data or not str(data[key]).strip()]
    if missing:
        raise RuntimeError(f"Missing keys in {config_path}: {missing}")
    return {key: str(data[key]).strip() for key in required}


def generate_launch_description():
    package_root = Path(__file__).resolve().parents[1]
    defaults = _load_launch_defaults(package_root)
    default_urdf = str((package_root / defaults["urdf_path"]).resolve())
    default_base = str((package_root / defaults["base_path"]).resolve())
    default_controllers_yaml = str((package_root / defaults["controllers_yaml"]).resolve())
    controllers_yaml_path = Path(default_controllers_yaml)
    controller_names = _controllers_to_spawn(controllers_yaml_path)

    urdf_path_arg = DeclareLaunchArgument(
        "urdf_path",
        default_value=default_urdf,
        description="Absolute path to robot URDF xacro",
    )
    base_path_arg = DeclareLaunchArgument(
        "base_path",
        default_value=default_base,
        description="Base path for xacro (mesh_dir)",
    )
    controllers_yaml_arg = DeclareLaunchArgument(
        "controllers_yaml",
        default_value=default_controllers_yaml,
        description="Absolute path to controller_manager YAML config",
    )
    urdf_path = LaunchConfiguration("urdf_path")
    base_path = LaunchConfiguration("base_path")
    controllers_yaml = LaunchConfiguration("controllers_yaml")

    robot_description = Command(["xacro ", urdf_path, " base_path:=", base_path])
    robot_description_dict = {"robot_description": robot_description}

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description_dict],
    )
    ros2_control_node = TimerAction(
        period=2.0,
        actions=[
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                output="screen",
                parameters=[controllers_yaml],
                remappings=[("~/robot_description", "/robot_description")],
            )
        ],
    )
    spawners = [
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=[controller],
            output="screen",
        )
        for controller in controller_names
    ]

    return LaunchDescription([
        urdf_path_arg, base_path_arg, controllers_yaml_arg,
        robot_state_publisher, ros2_control_node,
        *spawners,
    ])
