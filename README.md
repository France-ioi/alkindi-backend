# Description

This repository contains backend components (webservice) for the Alkindi
competition.

# Requirements

The following components are required:

  * python 3
  * a redis server
  * mysql
  * an oauth2 provider

On Debian "jessie" and "stretch", these instructions should work:

    # apt-get install python3 python3-venv python3-setuptools python3-wheel
    # apt-get install python3-mysql.connector python3-zope.interface python3-markupsafe python3-yaml
    $ pyven --system-site-packages ~/python

# Installation

As of version 0.7.9.53, the mysql dialect of sqlbuilder is broken and
requires a patch to work.  A solution is to install version 0.7.9.34
which is known to work:

    $ pip3 install -Iv 'https://pypi.python.org/packages/26/09/78b5336550fa977ffa68dfa9a73dd5f93084dd4b0a08e41baff2c18f7e18/sqlbuilder-0.7.9.34.tar.gz#md5=2cdba62ae995556b8e1e3e8e45be1880'

Install the python package for development:

    ./setup.py develop

Copy config_template.ini to config.ini and adjust the host and port
as needed.  This file also includes Pyramid settings that can be
useful for development.

Environment variables REDIS_HOST, REDIS_PORT, REDIS_DB should point
to the redis database.

Most configuration is stored in redis.  Use the configuration script
'configure.sh' at the root of the project to inject the configuration
in redis.

Starting the server:

    gunicorn --reload --paste config.ini

If using a local OAuth2 provider over an unsecure transport (http)
during development, set this environment variable when running the
application:

    OAUTHLIB_INSECURE_TRANSPORT=1
