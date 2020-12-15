import signal
import re
from gevent.pywsgi import WSGIServer
import logging
import queue
from threading import Thread
from time import sleep
import generic_taxii_connector
from dim_endpoints import controller_ingest, register_with_controller
from config import Config, Interval
from flask import Flask, request, jsonify, make_response, Response

from logger import LogConfig

stix_q = queue.Queue(1)

app = Flask(__name__)

# Disable Flask logs
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True


class ResponseError:
    error: str

    def error(self, error_message):
        self.error = error_message


def enq():
    if stix_q.full():
        old_thread = stix_q.get()
        old_thread.stop()
        stix_q.put(get_stix())
        return
    stix_q.put(get_stix())


class get_stix(Thread):
    loop = None

    def __init__(self):
        Thread.__init__(self)
        self.loop = True
        self.daemon = True
        self.start()

    def stop(self):
        self.loop = False

    def run(self):
        while self.loop:

            interval = Interval()
            interval.load()
            hours = interval.get('time-in-hours')

            if int(hours) == 0:
                return

            sleep_seconds = int(hours) * 60 * 60
            logging.info('starting taxii feed search')
            dims = generic_taxii_connector.generic_get_dim_objects()
            if dims['items'] != '':
                controller_ingest(dims)
            logging.info(f'{self.getName()} is sleeping for {hours} hours or {sleep_seconds} seconds')
            sleep(sleep_seconds)

        return


class flask_thread(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        http_server = WSGIServer(('0.0.0.0', 8080), app)
        http_server.serve_forever()


def list_to_csv(config_array):
    return ','.join(config_array)


@app.route('/run', methods=['POST'])
def run():
    print('')


@app.route('/health', methods=['GET'])
def health():
    resp = jsonify(success=True)
    return resp


@app.route('/config', methods=['GET', 'POST'])
def config():
    # Get config
    config = Config()
    config.load()

    interval = Interval()
    interval.load()

    if request.method == 'GET':
        providers = config.get_keys()
        init_discovery = []
        init_username = []
        init_password = []
        init_feeds = []

        for provider in providers:
            init_discovery.append(config.get(provider)['discovery'])
            init_username.append(config.get(provider)['username'])
            init_password.append(config.get(provider)['password'])
            init_feeds.append(config.get(provider)['feed'])

        data = {'fields': [
            {
                'label': 'Import interval',
                'type': 4,
                'expected_json_name': 'interval',
                'rationale': 'Enter how often findings will be imported from the feeds (hours).\nMake sure the import '
                             'interval is smaller than the expiration time of elements in the feed.',
                'value': interval.get('time-in-hours'),
                'possible_values': [],
                'required': True
            }, {
                'label': 'TAXII feed - URL list',
                'type': 9,
                'expected_json_name': 'discovery',
                'rationale': 'Enter the url of one or more feeds (seperated by comma).',
                'value': f'{list_to_csv(init_discovery)}',
                'possible_values': [],
                'required': True
            }, {
                'label': 'TAXII feed - API roots list',
                'type': 9,
                'expected_json_name': 'feed',
                'rationale': 'Enter the API root separating entries with comma, matching the order of the URLs.',
                'value': f'{list_to_csv(init_feeds)}',
                'possible_values': [],
                'required': False
            }, {
                'label': 'TAXII feed - Username list',
                'type': 9,
                'expected_json_name': 'username',
                'rationale': 'Enter the username of each feed  separating entries with comma, matching the order of '
                             'the URLs. Leave empty if no username is needed.',
                'value': f'{list_to_csv(init_username)}',
                'possible_values': [],
                'required': True
            }, {
                'label': 'TAXII feed - Password list',
                'type': 9,
                'expected_json_name': 'password',
                'rationale': 'Enter the password for each feed separating entries with comma, matching the order of '
                             'the URLs. Leave empty if no password is needed.',
                'value': f'{list_to_csv(init_password)}',
                'possible_values': [],
                'required': True
            }, {
                'label': 'Requirements',
                'type': 7,
                'expected_json_name': '',
                'rationale': 'Feed Format: TAXII 2.0\nElements Format: STIX 2.0\n\nClick the Help icon for further information on how to configure this module',
                'value': '',
                'possible_values': [],
                'required': False
            }, {
                'label': 'Elements imported',
                'type': 7,
                'expected_json_name': '',
                'rationale': 'IP addresses\nURLs\nDomains',
                'value': '',
                'possible_values': [],
                'required': False
            },
        ]}

        return make_response(jsonify(data), 200)
    else:
        try:
            request_data = request.get_json(force=True)
            interval_time = request_data['values'].pop('interval')
            logging.info(interval_time)

            if int(interval_time) <= 0:
                return Response("Please configure STIX module", status=501, mimetype='application/json')

            if request_data['values']['discovery'] == '' and request_data['values']['username'] == '' \
                    and request_data['values']['password'] == '' and request_data['values']['feed'] == '':
                request_data['values']['discovery'] = 'https://change-me.com/taxii/'
                request_data['values']['username'] = 'guest'
                request_data['values']['password'] = 'guest'
                request_data['values']['feed'] = 'feed'

            request_data['values']['discovery'] = string_stripper(request_data['values']['discovery'])
            request_data['values']['username'] = string_stripper(request_data['values']['username'])
            request_data['values']['password'] = string_stripper(request_data['values']['password'])
            request_data['values']['feed'] = string_stripper(request_data['values']['feed'])

            # IF the feeds are left blank add commas
            if request_data['values']['feed'] == '' or None:
                n = len(request_data['values']['discovery'].split(',')) - 1
                k = ','
                request_data['values']['feed'] = request_data['values']['feed'].ljust(n, k)

            config.update_config(request_data['values'])
            interval.update_config(interval_time)
            configured = config.is_configured()
            if configured:
                enq()

            register_with_controller(configured)
            resp = jsonify(success=True)
            return resp
        except Exception as e:
            logging.error(e)


def string_stripper(string_to_strip):
    return re.sub(r"[\n\t\s]*", "", string_to_strip)


class ProgramStop:
    stop = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.stop = True


if __name__ == "__main__":

    LogConfig()
    flask_thread()
    stop_me = ProgramStop()

    while not stop_me.stop:
        signal.pause()
