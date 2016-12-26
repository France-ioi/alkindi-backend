#!/usr/bin/env python3

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.md')) as f:
    CHANGES = f.read()

requires = [
    'mysql-connector >= 2.1.4',
    'zope.interface >= 4.1.1',
    'MarkupSafe >= 0.23',
    'PyYAML >= 3.11',
    'Babel >= 2.1.1',
    'gunicorn >= 19.4.1',
    'iso8601 >= 0.1.11',
    'Mako >= 1.0.3',
    'oauthlib >= 1.0.3',
    'PyJWT >= 1.4.0',
    'pyramid >= 1.6b3',
    'pyramid_debugtoolbar >= 2.4.2',
    'pyramid-mako >= 1.0.2',
    'pyramid_redis_sessions >= 1.0.1',
    'requests >= 2.9.0',
    'sqlbuilder-0.7.9.53',
    'ua-parser >= 0.6.1',
    'bleach >= 1.4.2',
    'unidecode >= 0.03'
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
