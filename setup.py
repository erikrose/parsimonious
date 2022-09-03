from sys import version_info

from io import open
from setuptools import setup, find_packages

long_description=open('README.rst', 'r', encoding='utf8').read()

setup(
    name='parsimonious',
    version='0.10.0',
    description='(Soon to be) the fastest pure-Python PEG parser I could muster',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author='Erik Rose',
    author_email='erikrose@grinchcentral.com',
    license='MIT',
    packages=find_packages(exclude=['ez_setup']),
    test_suite='tests',
    url='https://github.com/erikrose/parsimonious',
    include_package_data=True,
    install_requires=['regex>=2022.3.15'],
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing :: General'],
    keywords=['parse', 'parser', 'parsing', 'peg', 'packrat', 'grammar', 'language'],
)
