#!/usr/bin/env python3
# Copyright 2025 Sentience Robotics Team
#
# SPDX-License-Identifier: GPL-3.0-only

# Real robot / RViz-only: lucy_control_supervisor owns RSP + ros2_control_node + spawners.

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import yaml


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


def generate_launch_description():
    package_root = Path(__file__).resolve().parents[1]
    defaults = _load_launch_defaults(package_root)
    default_controllers_yaml = str(
        (package_root / defaults["controllers_yaml"]).resolve()
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
                    "gazebo_only": "false",
                    "autostart": "true",
                }.items(),
            )
        ],
    )

    return LaunchDescription(
        [
            controllers_yaml_arg,
            urdf_path_arg,
            base_path_arg,
            supervisor_launch,
        ]
    )
