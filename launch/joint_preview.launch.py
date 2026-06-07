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
URDF joint-limit preview: robot_state_publisher + joint_state_publisher_gui + RViz.

Sliders honor URDF <limit> tags. Use after editing robot_description.urdf.xacro
(or properties.xacro for model_scale).

  ros2 launch inmoov_urdf joint_preview.launch.py

Pass ``jsp_gui:=false`` to suppress the joint-state-publisher-gui sliders —
useful when an external publisher (e.g. ``scripts/autocalibrate_joint_limits.py
--view rviz``) drives ``/joint_states`` instead.
"""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _default_paths():
    try:
        share = Path(get_package_share_directory("inmoov_urdf"))
        root = share
    except Exception:
        root = Path(__file__).resolve().parents[1]
    description = root / "description"
    return (
        str(description / "urdf" / "inmoov.urdf.xacro"),
        str(description),
        str(root / "config" / "controllers.yaml"),
    )


def generate_launch_description():
    default_urdf, default_base, default_controllers = _default_paths()
    default_rviz = os.path.join(
        get_package_share_directory("inmoov_urdf"),
        "config",
        "inmoov_rviz.rviz",
    )

    urdf_path_arg = DeclareLaunchArgument(
        "urdf_path",
        default_value=default_urdf,
        description="Top-level inmoov xacro",
    )
    base_path_arg = DeclareLaunchArgument(
        "base_path",
        default_value=default_base,
        description="Description root (meshes, ros2_control paths)",
    )
    controllers_yaml_arg = DeclareLaunchArgument(
        "controllers_yaml",
        default_value=default_controllers,
        description="controllers.yaml for ros2_control xacro include",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_rviz,
        description="RViz display config",
    )
    jsp_gui_arg = DeclareLaunchArgument(
        "jsp_gui",
        default_value="true",
        description="Spawn joint_state_publisher_gui (set false when an external "
        "publisher drives /joint_states, e.g. autocalibrate_joint_limits.py --view rviz)",
    )

    urdf_path = LaunchConfiguration("urdf_path")
    base_path = LaunchConfiguration("base_path")
    controllers_yaml = LaunchConfiguration("controllers_yaml")

    # Force value_type=str so ROS 2 launch (Humble) does not try to YAML-parse
    # the xacro output. The URDF starts with `<?xml ...>`, which the YAML
    # loader rejects with "Unable to parse the value of parameter robot_description".
    robot_description = ParameterValue(
        Command(
            [
                "xacro ",
                urdf_path,
                " base_path:=",
                base_path,
                " use_gazebo_sim:=false",
                " use_mock_hardware:=true",
                " controller_config:=",
                controllers_yaml,
            ]
        ),
        value_type=str,
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )

    joint_state_publisher_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
        condition=IfCondition(LaunchConfiguration("jsp_gui")),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["--display-config", LaunchConfiguration("rviz_config")],
        parameters=[{"use_sim_time": False}],
    )

    return LaunchDescription(
        [
            urdf_path_arg,
            base_path_arg,
            controllers_yaml_arg,
            rviz_config_arg,
            jsp_gui_arg,
            robot_state_publisher,
            joint_state_publisher_gui,
            rviz,
        ]
    )
