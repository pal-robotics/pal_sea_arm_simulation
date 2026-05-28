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

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument, SetLaunchConfiguration
from launch.actions import OpaqueFunction
from launch.conditions import IfCondition
from launch_pal.include_utils import include_scoped_launch_py_description
from launch_pal.arg_utils import LaunchArgumentsBase
from launch_pal.robot_arguments import CommonArgs
from pal_sea_arm_description.launch_arguments import SEAArmArgs

from launch_ros.actions import Node


from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchArguments(LaunchArgumentsBase):
    end_effector: DeclareLaunchArgument = SEAArmArgs.end_effector
    ft_sensor: DeclareLaunchArgument = SEAArmArgs.ft_sensor
    wrist_model: DeclareLaunchArgument = SEAArmArgs.wrist_model
    moveit: DeclareLaunchArgument = CommonArgs.moveit
    world_name: DeclareLaunchArgument = CommonArgs.world_name
    arm_type: DeclareLaunchArgument = DeclareLaunchArgument(
        'arm_type', default_value='tiago-pro',
        choices=['pal-sea-arm-standalone', 'tiago-pro', 'tiago-sea', 'tiago-sea-dual'],
        description='The arm model')
    sim_type: DeclareLaunchArgument = CommonArgs.sim_type
    mj_control: DeclareLaunchArgument = CommonArgs.mj_control


def declare_actions(launch_description: LaunchDescription, launch_args: LaunchArguments):

    # Set use_sim_time to True
    set_sim_time = SetLaunchConfiguration('use_sim_time', 'True')
    launch_description.add_action(set_sim_time)

    # Set simulation_type to Mujoco Ros2 Control
    set_sim_type = SetLaunchConfiguration('sim_type', 'mujoco-ros2-control')
    launch_description.add_action(set_sim_type)

    # Set world for Mujoco simulation
    set_world_name = SetLaunchConfiguration('world_name', 'floor')
    launch_description.add_action(set_world_name)

    robot_bringup = include_scoped_launch_py_description(
        pkg_name='pal_sea_arm_bringup', paths=['launch', 'pal_sea_arm_bringup.launch.py'],
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "arm_type": launch_args.arm_type,
            "ft_sensor": launch_args.ft_sensor,
            "end_effector": launch_args.end_effector,
            "wrist_model": launch_args.wrist_model,
            "sim_type": LaunchConfiguration("sim_type"),
            "mj_control": LaunchConfiguration("mj_control"),
            "world_name": LaunchConfiguration("world_name"),
            })

    launch_description.add_action(robot_bringup)

    move_group = include_scoped_launch_py_description(
        pkg_name='pal_sea_arm_moveit_config',
        paths=['launch', 'move_group.launch.py'],
        launch_arguments={
            "ft_sensor": launch_args.ft_sensor,
            "end_effector": launch_args.end_effector,
            "wrist_model": launch_args.wrist_model,
            "arm_type": launch_args.arm_type,
            "use_sim_time": LaunchConfiguration("use_sim_time")},
        condition=IfCondition(LaunchConfiguration("moveit")))

    launch_description.add_action(move_group)

    # Launch the conversion node
    def converter_node_setup(context, *args, **kwargs):
        args_list = [
            "-p", "mujoco_robot_description",
            "--no-fuse"
        ]
        return [Node(
            package="mujoco_ros2_control",
            executable="robot_description_to_mjcf.sh",
            output="both",
            emulate_tty=True,
            arguments=args_list,
        )]

    launch_description.add_action(OpaqueFunction(function=converter_node_setup))

    # Mujoco Ros2 Control Simulation
    control_node = Node(
        package="mujoco_ros2_control",
        executable="ros2_control_node",
        output="both",
        parameters=[
            {"use_sim_time": LaunchConfiguration("use_sim_time")},
        ],
    )

    launch_description.add_action(control_node)

    return


def generate_launch_description():

    # Create the launch description
    ld = LaunchDescription()

    launch_arguments = LaunchArguments()

    launch_arguments.add_to_launch_description(ld)

    declare_actions(ld, launch_arguments)

    return ld
