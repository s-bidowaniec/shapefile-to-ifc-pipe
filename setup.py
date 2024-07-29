from setuptools import setup, find_packages

setup(
    name='shp_to_ifc_converter',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'geopandas',
        'ifcopenshell',
        'gooey',
    ],
    entry_points={
        'console_scripts': [
            'shp_to_ifc=src.main:main',
        ],
    },
)
