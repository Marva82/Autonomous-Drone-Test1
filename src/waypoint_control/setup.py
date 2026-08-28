from setuptools import find_packages, setup

package_name = 'waypoint_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='autonomous-drones-course',
    maintainer_email='aaronuram123@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
    'console_scripts': [
        'flyto_action_server = waypoint_control.flyto_action_server:main',
        'flyto_action_client = waypoint_control.flyto_action_client:main',
    ],
    },
)
