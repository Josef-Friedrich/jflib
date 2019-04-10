from setuptools import setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='jflib',
    author='Josef Friedrich',
    author_email='josef@friedrich.rocks',
    description=('A collection of my Python scripts. Maybe they are useful for someone else.'),
    license='MIT',
    project_urls={
        'Documentation': 'http://jflib.readthedocs.io/en/latest/',
        'Source': 'https://github.com/Josef-Friedrich/jflib',
        'Tracker': 'https://github.com/Josef-Friedrich/jflib/issues',
    },
    packages=['jflib'],
    url='https://github.com/Josef-Friedrich/python-scripts',
    python_requires='>=3.6',
    long_description=read('README.md'),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
)
