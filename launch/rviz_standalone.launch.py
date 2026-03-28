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
RViz2 only — no robot_state_publisher, no ros2_control, no Gazebo.

Use when another stack already publishes /robot_description and /joint_states
(e.g. lucy_bringup lucy.launch.py + lucy_ros2_control control.launch.py).

Terminal 1:
  ros2 launch lucy_bringup lucy.launch.py

Terminal 2:
  ros2 launch thais_urdf rviz_standalone.launch.py

For a single machine that starts control + rosbridge + RViz together, use rviz.launch.py instead.
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_rviz = os.path.join(
        get_package_share_directory("thais_urdf"),
        "config",
        "inmoov_rviz.rviz",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "rviz_config",
                default_value=default_rviz,
                description=(
                    "Display config .rviz path "
                    "(default: inmoov_rviz.rviz in this package)"
                ),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=[
                    "--display-config",
                    LaunchConfiguration("rviz_config"),
                ],
                parameters=[{"use_sim_time": False}],
            ),
        ]
    )
