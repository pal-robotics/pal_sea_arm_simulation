# Copyright (c) 2024 PAL Robotics S.L. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python import get_package_share_directory

from launch import LaunchDescription
from launch.actions import SetLaunchConfiguration, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import LaunchConfigurationEquals

from launch_ros.actions import Node
from dataclasses import dataclass
from launch_pal.arg_utils import LaunchArgumentsBase
from launch_pal.robot_arguments import CommonArgs


@dataclass(frozen=True)
class LaunchArguments(LaunchArgumentsBase):
    gazebo_version: DeclareLaunchArgument = CommonArgs.gazebo_version


def generate_launch_description():

    # Create the launch description
    ld = LaunchDescription()
    launch_arguments = LaunchArguments()

    launch_arguments.add_to_launch_description(ld)

    declare_actions(ld, launch_arguments)

    return ld


def declare_actions(launch_description: LaunchDescription, launch_args: LaunchArguments):

    set_arm_model = SetLaunchConfiguration('robot_name', 'pal_sea_arm')
    launch_description.add_action(set_arm_model)

    robot_entity = Node(package='gazebo_ros', executable='spawn_entity.py',
                        arguments=['-topic', 'robot_description',
                                   '-entity', LaunchConfiguration('robot_name'),
                                   "-x", "0.0", "-y", "0.0", "-z", "0.08",
                                   ],
                        output='screen',
                                condition=LaunchConfigurationEquals('gazebo_version', 'classic')
                        )
    launch_description.add_action(robot_entity)

    gazebo_spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-model",
            LaunchConfiguration("robot_name"),
            "-topic",
            "robot_description",
        ],
        condition=LaunchConfigurationEquals('gazebo_version', 'gazebo'),
    )
    launch_description.add_action(gazebo_spawn_robot)

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='bridge_ros_gz',
        parameters=[{
            'config_file': os.path.join(
                get_package_share_directory('pal_sea_arm_gazebo'),
                'config', 'pal_sea_arm_gz_bridge.yaml'),
            'use_sim_time': True,
        }],
        output='screen',
        condition=LaunchConfigurationEquals('gazebo_version', 'gazebo'),
    )
    launch_description.add_action(bridge)

    return
