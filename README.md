# Description

This repository contains the backend components for the Alkindi
competition, rounds 2 to 4.

# Requirements

The following software components are required:

* node.js

    $ nvm install v5.3.0
    $ nvm alias default v5.3.0
    $ npm install -g gulp
    $ (cd ~/alkindi-r2-front; npm install; gulp; cd dist_python; ./setup.py build develop)

* python 3

    # apt-get install python3 python3-venv python3-setuptools
    # apt-get install python3-psycopg2 python3-zope.interface python3-markupsafe python3-yaml
    $ pyvenv-3.4 --system-site-packages ~/python
    $ (cd ~/alkindi-r2-front/dist_python; ./setup.py develop)
    $ (cd ~/alkindi-r2-back; ./setup.py develop)

In addition, the following external services are used:

* redis
* postgresql
* an oauth2 provider

    # apt-get install openssh-server curl less
    # apt-get install postgresql-9.4 libpq-dev redis-server

# Installation

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
