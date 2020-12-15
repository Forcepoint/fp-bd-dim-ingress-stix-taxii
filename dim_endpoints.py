import os
import requests
import logging


def _get_dim_url(endpoint):
    service_name = os.getenv('CONTROLLER_SVC_NAME')
    port = os.getenv('CONTROLLER_PORT')

    url_string = 'http://'
    url_string = url_string + service_name + ':' + port + endpoint
    print(url_string)
    return url_string


def controller_ingest(dim_objects):
    registration_url = _get_dim_url('/internal/queue')
    r = requests.post(registration_url, json=dim_objects,
                      headers={'x-internal-token': os.getenv('INTERNAL_TOKEN'), 'Content-Type': 'application/json'})

    logging.info(f'Ingest code: {r.status_code}')


def register_with_controller(configured):
    registration_url = _get_dim_url('/internal/register')
    icon_url = os.getenv('ICON_URL')
    payload = {
        'icon_url': str(icon_url),
        'module_service_name': 'fp-stix-taxii',
        'module_display_name': 'TAXII Feed Connector',
        'module_type': 'ingress',
        'module_description': 'Ingests intelligence by connecting to one or more TAXII feeds and receives elements '
                              'distributed using the stix format',
        'inbound_route': '/fp-stix-taxii',
        'internal_ip': '1.2.3.4',
        'internal_port': '8080',
        'configured': configured,
        'configurable': True,
        'internal_endpoints': [
            {'secure': True, 'endpoint': '/run', 'http_methods': [{'method': 'OPTIONS'}, {'method': 'POST'}]},
            {'secure': True, 'endpoint': '/health', 'http_methods': [{'method': 'OPTIONS'}, {'method': 'GET'}]},
            {'secure': True, 'endpoint': '/config',
             'http_methods': [{'method': 'OPTIONS'}, {'method': 'GET'}, {'method': 'POST'}]}
        ]
    }

    r = requests.post(registration_url, json=payload,
                      headers={'x-internal-token': os.getenv('INTERNAL_TOKEN'), 'Content-Type': 'application/json'})

    logging.info(f'Register code: {r.status_code}')
