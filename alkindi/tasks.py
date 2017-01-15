
import requests
import json
import urllib.parse


def task_generate(backend_url, params, seed, auth=None):
    generate_url = urllib.parse.urljoin(backend_url, 'generate')
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    if auth is not None:
        headers['Authorization'] = auth
    body = {
        'params': params,
        'seed': seed
    }
    req = requests.post(
        generate_url, headers=headers, data=json.dumps(body),
        verify='/etc/ssl/certs/ca-certificates.crt')
    req.raise_for_status()
    result = req.json()
    if 'task' not in result or 'full_task' not in result:
        raise RuntimeError('bad task generator {}'.format(generate_url))
    return (result['task'], result['full_task'])


def task_get_hint(backend_url, full_task, query, auth=None):
    pass
