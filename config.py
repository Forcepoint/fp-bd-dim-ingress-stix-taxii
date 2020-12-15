import yaml
import uuid
import os.path
from os import path


class Interval:
    data = {}

    def load(self):
        # Load in config file details
        try:
            with open('config/update_interval.yaml') as config:
                self.data = yaml.load(config, Loader=yaml.FullLoader)
        except FileNotFoundError:

            with open('config/update_interval.yaml', 'w') as f:
                update_interval_file = {'time-in-hours': '0'}
                yaml.dump(update_interval_file, f)
                self.load()

    def get(self, key):
        return self.data.get(key, None)

    def update_config(self, hours):
        with open('config/update_interval.yaml', 'w+') as config:
            self.data['time-in-hours'] = hours
            self.data = yaml.dump(self.data, config)
        self.load()


class Config:
    """
    Class representing configuration for the program.
    """
    data = {}

    def is_configured(self):

        keys = self.get_keys()
        for key in keys:
            if self.data[key]['discovery'] != 'https://change-me.com/taxii/':
                return True
            else:
                return False

    def write_keys(self, data):
        #thing = '' + '!!omap' + data
        with open('config/config.yaml', 'w+') as config:
            self.data = yaml.dump(data, config, sort_keys=False)

    def load(self):
        # Load in config file details
        try:
            with open('config/config.yaml') as config:
                self.data = yaml.load(config, Loader=yaml.FullLoader)
        except FileNotFoundError:
            if path.exists('config'):
                with open('config/config.yaml', 'w') as f:
                    init_dict = {str(uuid.uuid4()): {'discovery': 'https://change-me.com/taxii/', 'username': 'guest',
                                                     'password': 'guest', 'feed': 'feed',
                                                     'last-update': '0001-01-01T00:00:00.000Z'}}
                    yaml.dump(init_dict, f)
                    self.load()
            else:
                os.mkdir('config')
                self.load()

    def get(self, key):
        return self.data.get(key, None)

    def get_keys(self):
        try:
            return [key for key, value in self.data.items()]
        except AttributeError:
            return None

    def update_field_by_key(self, key, field, value):
        data = self.data
        data[key][field] = value
        self.write_keys(data)
        self.load()

    def update_config(self, new_fields):
        temp_dict = {}
        existing_keys = self.get_keys()
        length_of_csv_values = len(new_fields[list(new_fields.keys())[0]].split(','))
        for i in range(length_of_csv_values):
            new_uuid = str(uuid.uuid4())
            temp_dict[new_uuid] = {'discovery': new_fields['discovery'].split(',')[i],
                                   'username': new_fields['username'].split(',')[i],
                                   'password': new_fields['password'].split(',')[i],
                                   'feed': new_fields['feed'].split(',')[i],
                                   'last-update': '0001-01-01T00:00:00.000Z'}
            if existing_keys is not None:
                for existing_key in existing_keys:
                    existing_dict = {'discovery': self.get(existing_key)['discovery'],
                                     'username': self.get(existing_key)['username'],
                                     'password': self.get(existing_key)['password'],
                                     'feed': self.get(existing_key)['feed'],
                                     'last-update': self.get(existing_key)['last-update']}

                    if temp_dict[new_uuid]['discovery'] == existing_dict['discovery'] and temp_dict[new_uuid][
                        'username'] == existing_dict['username'] and temp_dict[new_uuid]['password'] == existing_dict[
                        'password'] and temp_dict[new_uuid]['feed'] == existing_dict['feed']:
                        temp_dict.pop(new_uuid)
                        temp_dict[existing_key] = existing_dict
                        new_uuid = existing_key

        self.write_keys(temp_dict)
        self.load()
