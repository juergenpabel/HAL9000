#!/usr/bin/python3

import sys
from flask import Flask, Blueprint
from configparser import ConfigParser

from pyjserver.endpoint.errorhandler import make_errorhandler
from pyjserver.endpoint.methods import make_default_method, make_crud_method
from pyjserver.database.connector import Connector

app = Flask(__name__)
app_conf = ConfigParser(delimiters='=', converters={'list':   lambda list:   [item.strip().strip('"').strip("'") for item in list.split(',')],
                                                    'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
app_conf.read(sys.argv[1])
for storage_endpoint in app_conf.getlist('rest', 'endpoints', fallback=[]):
	storage_filename = app_conf['storage'].getstring(storage_endpoint)
	with Connector(storage_filename) as connector:
		endpoints = list(connector.json_data.endpoints)
		for endpoint in list(connector.json_data.endpoints):
			blueprint = Blueprint(endpoint, endpoint, url_prefix=f'/{storage_endpoint}/{endpoint}')
			blueprint.add_url_rule('/',                 'get-all',    make_crud_method(storage_filename, endpoint, method='get'),    methods=['GET'])
			blueprint.add_url_rule('/<int:identifier>', 'get-one',    make_crud_method(storage_filename, endpoint, method='get'),    methods=['GET'])
			blueprint.add_url_rule('/',                 'post-one',   make_crud_method(storage_filename, endpoint, method='post'),   methods=['POST'])
			blueprint.add_url_rule('/<int:identifier>', 'put-one',    make_crud_method(storage_filename, endpoint, method='put'),    methods=['PUT'])
			blueprint.add_url_rule('/<int:identifier>', 'delete-one', make_crud_method(storage_filename, endpoint, method='delete'), methods=['DELETE'])
			app.register_blueprint(blueprint, name=f"{storage_endpoint}/{endpoint}")
			print(f"registered REST endpoint: /{storage_endpoint}/{endpoint}/")
for code in [400, 401, 403, 404, 405, 500, 501, 502, 503]:
	app.register_error_handler(code, make_errorhandler())

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8080, debug=True)

