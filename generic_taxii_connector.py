import logging

import requests
from requests.exceptions import MissingSchema
import taxii_connect
from config import Config


def _get_dim_objects(root, last_update):
    last_update, base_stix, extra_properties_stix, custom_properties_stix = \
        taxii_connect.unpack_stix_bundle(root, last_update)

    extracted_data = [taxii_connect.stix_pattern_extract(stix_list_item['pattern'])
                      for stix_list_item in base_stix
                      if 'pattern' in stix_list_item.keys()]

    dim_object_list = [taxii_connect.create_dim_objects(data) for data in extracted_data]
    dim_object_list = [i for i in dim_object_list if i]
    return dim_object_list, last_update


def generic_get_dim_objects():
    config = Config()
    config.load()
    providers = config.get_keys()
    temp_list = []
    blank_list = {'items': ''}
    if providers is None:

        return blank_list

    elif providers is not None:
        for provider in providers:

            discovery = config.get(provider)['discovery']
            username = config.get(provider)['username']
            password = config.get(provider)['password']
            feeds = config.get(provider)['feed']
            last_update = config.get(provider)['last-update']

            # Instantiate server and get API Root
            try:
                try:
                    server = taxii_connect.server_connect(discovery, username, password)
                except IndexError:
                    temp_list = temp_list + []
            except MissingSchema:
                temp_list = temp_list + []
            try:
                if feeds != '' and server.api_roots:
                    for root in server.api_roots:
                        if str(root.url).endswith(feeds + '/'):
                            dim_object_list, last_update = _get_dim_objects(root, last_update)
                            temp_list = temp_list + dim_object_list
                    config.update_field_by_key(provider, 'last-update', last_update)
                elif server.default:
                    dim_object_list, last_update = _get_dim_objects(server.default, last_update)
                    temp_list = temp_list + dim_object_list
                elif len(server.api_roots) == 1:
                    dim_object_list, last_update = _get_dim_objects(server.api_roots[0], last_update)
                    temp_list = temp_list + dim_object_list
            except requests.exceptions.HTTPError as e:
                logging.info(str(e.args))

    items = {'items': temp_list}
    return items
