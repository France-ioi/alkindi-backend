#!/bin/bash

# Without this setting, the application will fail with a fatal error
# pointing to this configuration script.
redis-cli set configured yes

# app_base should point to the URL at which the application is published.
# Do not add a trailing slash.
redis-cli set app_base http://127.0.0.1:8001

# app_assets should point to a URL where (a copy of) the assets are published.
# In a production environment, this will typically be a CDN.
# Do not add a trailing slash.
redis-cli set assets_base http://127.0.0.1:8001/assets

# XXX This is a temporary setting (directory containing the source
#     assets).  Ultimately we want to use built assets.
redis-cli set assets_path $(pwd)/assets

# Regenerate the assets_timestamp whenever the assets are changed, to
# ensure that all clients get an up-to-date version.
redis-cli set assets_timestamp $(date +%s)

# Generate a random session secret.  Changing the secret invalidates all
# sessions.
redis-cli set session_secret $(python -c 'import uuid; print(uuid.uuid4())')

# cookie_max_age sets how long the browser will keep the cookie that
# stores the redis session identifier (604800 is 7 days in seconds).
redis-cli set session_settings '{"cookie_max_age":604800}'

# Configure oauth here.
redis-cli set oauth_client_id       'alkindi'
redis-cli set oauth_client_secret   'BpabOSwEwQ4O2+FjUg7YdrcheCXDEdquxAOV9GasLLqewpx9f0M1KpQELmvQ+A6R'
redis-cli set oauth_authorise_uri   'http://127.0.0.1:3000/oauth/authorise'
redis-cli set oauth_token_uri       'http://127.0.0.1:3000/oauth/token'
redis-cli set oauth_refresh_uri     'http://127.0.0.1:3000/oauth/token'

# Configure the identity provider endpoint here.
# This endpoint should accept an access token and return the authenticated
# user's profile.
redis-cli set identity_provider_uri 'http://127.0.0.1:3000/profile'
