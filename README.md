# Description

This repository contains the backend components for the Alkindi
competition, rounds 2 to 4.

# Requirements

The following software components are required:

* python 3
* node.js

In addition, the following external services are used:

* redis
* postgresql
* an oauth2 provider

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
