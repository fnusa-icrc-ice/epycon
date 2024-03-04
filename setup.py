from setuptools import setup, find_packages

setup(
    name='epycon',
    version='1.02',
    description='A Single-Platform Python Package for Parsing and Converting Raw Electrophysiology Data into Open Formats',
    url='',    
    author='FNUSA-ICRC',
    author_email='jakub.hejc@fnusa.cz',
    packages=find_packages(),
    install_requires=[
        'h5py',
        'jsonschema',
        'numpy',            
        ],    
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        ],    
    zip_safe=False,
      )