#!/usr/bin/env python3

from setuptools import find_packages, setup
import os

# You need install_requires if you don't have a ROS environment
install_requires = [  # ] if os.environ.get('AMENT_PREFIX_PATH') else [
    # build
    'setuptools',
    # runtime
    'python3-pigpio',
    'guizero'
]

tests_require = []

extras_require = {}

d = setup(
    name='tripipy',
    version='0.1.0',  # also update package.xml and version.py
    packages=find_packages(),
    install_requires=install_requires,
    extras_require=extras_require,
    author='pootle',
    maintainer='pootle',
    url='https://github.com/pootle/tripipy',
    keywords='tmc5130, tmc5160',
    zip_safe=True,
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: Unlicense',
        'Programming Language :: Python',
        'Topic :: Engineering :: driver'
    ],
    description="pythonic implementation of trinamic motor controllers",
    long_description="This enables the control of TMC2130 and TMC5160.",
    license='Unlicense',
    test_suite='',
    tests_require=tests_require,
    entry_points={
        'console_scripts': [
            'py-trees-render = examples.motors2:main',
        ],
    },
)