from sys import version_info

# Prevent spurious errors during `python setup.py test` in 2.6, a la
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html:
try:
    import multiprocessing
except ImportError:
    pass

from io import open
from setuptools import setup, find_packages

long_description=open('README.rst', 'r', encoding='utf8').read()

setup(
    name='parsimonious',
    version='0.7.0',
    description='(Soon to be) the fastest pure-Python PEG parser I could muster',
    long_description=long_description,
    author='Erik Rose',
    author_email='erikrose@grinchcentral.com',
    license='MIT',
    packages=find_packages(exclude=['ez_setup']),
    tests_require=['nose'],
    test_suite='nose.collector',
    url='https://github.com/erikrose/parsimonious',
    include_package_data=True,
    install_requires=['six'],
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing :: General'],
    keywords=['parse', 'parser', 'parsing', 'peg', 'packrat', 'grammar', 'language'],
)
