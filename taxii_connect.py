import dataclasses
import json
import logging
import re
import os
from enum import Enum

import dateutil.parser
import stix2
from requests import exceptions
from stix2.exceptions import ParseError, ExtraPropertiesError
from taxii2client.v20 import Server
from dataclasses import dataclass
from stix2 import parse


def pattern_type(message_type):
    if message_type == 'ipv4addrvalue':
        return dim_type.IP.value
    elif message_type == 'domainnamevalue':
        return dim_type.DOMAIN.value
    elif message_type == 'urlvalue':
        return dim_type.URL.value
    else:
        return dim_type.NONE.value


class dim_type(Enum):
    NONE = 0
    IP = 1
    DOMAIN = 2
    URL = 3
    RANGE = 4


def stix_pattern_extract(stix_pattern):
    pattern_list = stix_pattern.split()
    pattern_list[0] = re.sub(r'\W+', '', pattern_list[0])
    pattern_list[-1] = pattern_list[-1][1:-2]
    del pattern_list[1]
    return pattern_list


def server_connect(discovery, username, password):
    try:
        server = Server(discovery, user=username, password=password)
        return server
    except exceptions.ConnectionError:
        logging.info(exceptions.ConnectionError())
        return None


def unpack_stix_bundle(root, last_update):
    base_stix = []
    extra_properties_stix = []
    custom_properties_stix = []

    for collections in root.collections:

        for stix in collections.get_objects()['objects']:

            if 'modified' in stix:
                if dateutil.parser.parse(stix['modified']) > (dateutil.parser.parse(stix['created']) and dateutil.parser.parse(last_update)):
                    last_update = stix['modified']
            elif 'created' in stix:
                if dateutil.parser.parse(stix['created']) > dateutil.parser.parse(last_update):
                    last_update = stix['created']

            try:
                try:
                    base_stix.append(parse(stix))
                except (ExtraPropertiesError, stix2.exceptions.InvalidValueError):
                    extra_properties_stix.append(stix)
            except ParseError:
                custom_properties_stix.append(parse(stix, allow_custom=True))

    return last_update, base_stix, extra_properties_stix, custom_properties_stix


def create_dim_objects(data):

    dim_object = _dim_Format(source='TAXII', service_name=os.getenv('MODULE_SVC_NAME'), value=data[1],
                             type=dim_type(pattern_type(data[0])).name)

    if dim_object.type == dim_type(0).name:
        return None

    return dim_object.to_dict()


@dataclass
class _dim_Format:
    source: str
    service_name: str
    type: dim_type
    value: str
    safe: bool = False

    def to_json(self):
        return json.dumps(dataclasses.asdict(self))

    def to_dict(self):
        return dataclasses.asdict(self)
