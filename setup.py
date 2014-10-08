from sys import version_info

# Prevent spurious errors during `python setup.py test` in 2.6, a la
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html:
try:
    import multiprocessing
except ImportError:
    pass

from setuptools import setup, find_packages


setup(
    name='parsimonious',
    version='0.6.2',
    description='(Soon to be) the fastest pure-Python PEG parser I could muster',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='erikrose@grinchcentral.com',
    license='MIT',
    packages=find_packages(exclude=['ez_setup']),
    tests_require=['nose'],
    test_suite='nose.collector',
    url='https://github.com/erikrose/parsimonious',
    include_package_data=True,
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
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing :: General'],
    keywords=['parse', 'parser', 'parsing', 'peg', 'packrat', 'grammar', 'language'],
    use_2to3=version_info >= (3,)
)
