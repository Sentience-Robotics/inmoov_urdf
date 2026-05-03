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

# Real robot + RViz + rosbridge. Control stack comes from control.launch.py.
from pathlib import Path

from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_root = Path(__file__).resolve().parents[1]
    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(package_root / "launch" / "control.launch.py"))
    )

    rosbridge = ExecuteProcess(
        cmd=["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"],
        output="screen",
        shell=True,
    )

    rviz_config = PathJoinSubstitution([
        FindPackageShare("thais_urdf"), "config", "inmoov_rviz.rviz",
    ])
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["--display-config", rviz_config],
        parameters=[{"use_sim_time": False}],
    )

    return LaunchDescription([
        control_launch,
        rosbridge,
        rviz,
    ])
