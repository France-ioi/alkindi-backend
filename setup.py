#!/usr/bin/env python3

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.md')) as f:
    CHANGES = f.read()

requires = [
    'pyramid >= 1.6b3',
    'pyramid_debugtoolbar',
    'pyramid_redis_sessions >= 1.0a3',
    'PyYAML >= 3.11',
    'iso8601 >= 0.1',
    'Babel >= 1.3',
    'psycopg2 >= 2.5',
    'gunicorn >= 19.4',
    'PyJWT >= 1.4',
    'oauthlib >= 1.0',
    'requests >= 2.9',
    'alkindi-r2-front'
]

packages = find_packages()

setup(
    name='alkindi-r2-back',
    version='2',
    description='Backend for Alkindi competition rounds 2 to 4',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python :: 3.4",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Sébastien Carlier',
    author_email='s.carlier@epixode.fr',
    keywords='web pyramid',
    packages=packages,
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    test_suite='alkindi',
    entry_points="""\
    [paste.app_factory]
    main = alkindi:backend
    """,
    data_files=[]
)
