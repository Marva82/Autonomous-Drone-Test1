import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'patrol_params_demo'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    # The YAML files
    (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    # NEW: The Launch files
    (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    description='Demonstration of ROS 2 Parameters, YAML, and constraints',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
    'patrol_node = patrol_params_demo.patrol_config:main',
    'mission_commander = patrol_params_demo.mission_commander:main',
    ],
    },
)