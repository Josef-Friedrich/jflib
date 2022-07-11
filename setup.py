import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='jflib',
    author='Josef Friedrich',
    author_email='josef@friedrich.rocks',
    description=('A collection of my Python library snippets. Maybe they are '
                 'useful for someone else.'),
    version='0.0.0',
    license='MIT',
    project_urls={
        'Documentation': 'http://jflib.readthedocs.io/en/latest/',
        'Source': 'https://github.com/Josef-Friedrich/jflib',
        'Tracker': 'https://github.com/Josef-Friedrich/jflib/issues',
    },
    packages=['jflib'],
    url='https://github.com/Josef-Friedrich/jflib',
    python_requires='>=3.5',
    long_description=read('README.md'),
    install_requires=[
       'typing-extensions==4.3.0',
       'requests==2.28.1'
    ],
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
