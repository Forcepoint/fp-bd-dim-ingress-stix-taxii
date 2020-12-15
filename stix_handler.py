import logging
from time import sleep
from config import Interval
from dim_endpoints import controller_ingest
import generic_taxii_connector
from logger import LogConfig


def get_stix():

    logging.info('starting taxii feed search')
    dims = generic_taxii_connector.generic_get_dim_objects()
    controller_ingest(dims)


def start_taxii_read():

    while True:
        LogConfig()
        interval = Interval()
        interval.load()
        hours = interval.get('time-in-hours')
        sleep_seconds = hours * 60 * 60
        get_stix()
        logging.info(f'Sleeping for {hours} hours or {sleep_seconds} seconds')
        sleep(sleep_seconds)


start_taxii_read()
