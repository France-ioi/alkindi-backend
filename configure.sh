#!/bin/bash

# mysql password (must be escaped for inclusion in JSON)
MYSQL_PASSWORD="MYSQL_PASSWORD"

# Without this setting, the application will fail with a fatal error
# pointing to this configuration script.
redis-cli set configured yes

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
redis-cli set oauth_authorise_uri   'https://oauth.epixode.fr/oauth/authorise'
redis-cli set oauth_token_uri       'https://oauth.epixode.fr/oauth/token'
redis-cli set oauth_refresh_uri     'https://oauth.epixode.fr/oauth/token'

# Configure the identity provider endpoint here.
# This endpoint should accept an access token and return the authenticated
# user's profile.
redis-cli set identity_provider_uri 'https://oauth.epixode.fr/profile'

# Configure the connection to mysql.
redis-cli set mysql_connection "{\"host\":\"localhost\",\"user\":\"alkindi\",\"passwd\":\"${MYSQL_PASSWORD}\",\"db\":\"alkindi\"}"

redis-cli set requested_badge 'https://badges.concours-alkindi.fr/qualification_tour2/2017'