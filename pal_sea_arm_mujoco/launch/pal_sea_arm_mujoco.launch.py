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
import yaml
from os import environ, pathsep

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument, SetLaunchConfiguration,OpaqueFunction
from launch.conditions import IfCondition
from launch_pal.include_utils import include_scoped_launch_py_description
from launch_pal.arg_utils import LaunchArgumentsBase
from launch_pal.robot_arguments import CommonArgs
from pal_sea_arm_description.launch_arguments import SEAArmArgs

from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch_pal.param_utils import merge_param_files

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
    mujoco: DeclareLaunchArgument = CommonArgs.mujoco
    mj_control: DeclareLaunchArgument = CommonArgs.mj_control
    mj_simulate: DeclareLaunchArgument = CommonArgs.mj_simulate

def declare_actions(launch_description: LaunchDescription, launch_args: LaunchArguments):

    set_sim_time = SetLaunchConfiguration('use_sim_time', 'True')
    launch_description.add_action(set_sim_time)

    set_mujoco = SetLaunchConfiguration('mujoco', 'true')
    launch_description.add_action(set_mujoco)

    set_end_effector = SetLaunchConfiguration('end_effector','pal-pro-gripper')
    launch_description.add_action(set_end_effector)

    set_wrist_model = SetLaunchConfiguration('wrist_model','spherical-wrist')
    launch_description.add_action(set_wrist_model)

    set_arm_type = SetLaunchConfiguration('arm_type','tiago-pro')
    launch_description.add_action(set_arm_type)

    # Import controller configuration files
    pal_sea_arm_controller_path = os.path.join(get_package_share_directory('pal_sea_arm_controller_configuration'))
    pal_pro_gripper_controller_path = os.path.join(get_package_share_directory('pal_pro_gripper_controller_configuration'))
    inference_controller_path= os.path.join(get_package_share_directory('arm_controller'))
 
    controller_manager_config_yaml = os.path.join(pal_sea_arm_controller_path, 'config', 'mujoco_controller_manager_cfg.yaml')
    joint_state_broadcaster_yaml = os.path.join(pal_sea_arm_controller_path, 'config', 'joint_state_broadcaster.yaml')
    arm_controller_yaml = os.path.join(pal_sea_arm_controller_path, 'config', 'arm_controller.yaml')
    inference_controller_yaml = os.path.join(inference_controller_path, 'config', 'joint_group_position_controller.yaml')
    pal_pro_gripper_controller_yaml = os.path.join(pal_pro_gripper_controller_path, 'config', 'gripper_controller.yaml')

    
    pal_sea_controller_yaml = generate_arm_controller_configs(arm_controller_yaml, pal_sea_arm_controller_path )
    gripper_controller_yaml = generate_gripper_controller_configs(pal_pro_gripper_controller_yaml, pal_pro_gripper_controller_path)

   
    merged_yaml = merge_param_files([
                                    controller_manager_config_yaml,
                                    inference_controller_yaml,
                                    pal_sea_controller_yaml, 
                                    joint_state_broadcaster_yaml,
                                    gripper_controller_yaml,
                                    ])
    
    launch_description.add_action(OpaqueFunction(
        function=mujoco_model_publisher))

    node_mujoco_ros2_control = Node(
        package='mujoco_ros2_control',
        executable='mujoco_ros2_control',
        output='screen',
        parameters=[merged_yaml, {'use_sim_time': True}],
    ) 
    launch_description.add_action(node_mujoco_ros2_control)

    robot_bringup = include_scoped_launch_py_description(
        pkg_name='pal_sea_arm_bringup', paths=['launch', 'pal_sea_arm_bringup.launch.py'],
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "arm_type": launch_args.arm_type,
            "ft_sensor": launch_args.ft_sensor,
            "end_effector": launch_args.end_effector,
            "wrist_model": launch_args.wrist_model,
            'mujoco': LaunchConfiguration('mujoco'),
            'mj_control': LaunchConfiguration('mj_control'),
            'mj_simulate': LaunchConfiguration('mj_simulate'),
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


    return

def mujoco_model_publisher(context, *args, **kwargs):
    xacro_input_args = {
            "robot_name": "pal_sea_arm",
            "mujoco": LaunchConfiguration("mujoco").perform(context),
            "mj_control": LaunchConfiguration("mj_control").perform(context),
            "mj_simulate": LaunchConfiguration("mj_simulate").perform(context),
            "end_effector": LaunchConfiguration("end_effector"),
            "arm_type": LaunchConfiguration("arm_type"),
            "wrist_model": LaunchConfiguration("wrist_model"),
    }
    
    model_pub = Node(
        package='pal_mujoco_model_loader_ros',
        executable='publisher',
        parameters=[xacro_input_args],
        output='screen'
    )
    
    return [model_pub]

def generate_arm_controller_configs(arm_controller_yaml, pal_sea_arm_controller_path):

  # Manage argument in the controller configuration file
    with open(arm_controller_yaml, 'r') as f:
        content = f.read()
    arm_content = content.replace('${ARM_SIDE_PREFIX}', f'arm')
    pal_sea_controller_yaml = os.path.join(pal_sea_arm_controller_path, 'config', f'pal_sea_controller_yaml')
    
    with open(pal_sea_controller_yaml, 'w') as arm_file:
        arm_file.write(arm_content)
    return pal_sea_controller_yaml

def generate_gripper_controller_configs(pal_pro_gripper_controller_yaml, pal_pro_gripper_controller_path):
    
    # Manage argument in the controller configuration file
    with open(pal_pro_gripper_controller_yaml, 'r') as file:
        content = file.read()

    gripper_content = content.replace('${EE_SIDE_PREFIX}', f'gripper')
    gripper_controller_yaml = os.path.join(pal_pro_gripper_controller_path, 'config', f'pal_pro_gripper_controller.yaml')
    
    with open(gripper_controller_yaml, 'w') as left_file:
        left_file.write(gripper_content)
    
    return gripper_controller_yaml

def generate_launch_description():

    # Create the launch description
    ld = LaunchDescription()

    launch_arguments = LaunchArguments()

    launch_arguments.add_to_launch_description(ld)

    declare_actions(ld, launch_arguments)

    return ld

