import http
import json
import logging
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

import simplejson as simplejson


class WebScenarioBuilderHttpRequestHandler(SimpleHTTPRequestHandler):
    def sluggifyRequests(self, requests):
        r = []
        for request in requests:
            r.append({
                'method': request.method,
                'url': '{}://{}{}'.format(request.scheme, request.host, request.path)
            })
        return r

    def do_POST(self):
        response = {'success': False, 'requests': []}
        if self.path == '/start_recording':
            self.server.proxy.start_recording()
            response['success'] = True
        if self.path == '/stop_recording':
            response['requests'] = self.sluggifyRequests(self.server.proxy.stop_recording())
            response['success'] = True
        if self.path == '/push_zabbix':
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))
            data = simplejson.loads(self.data_string)
            if not 'filter' in data:
                data['filter'] = '.*'
            zapi_result = self.server.zapi.push(data['host_key'], data['scenario_name'],
                                                self.server.proxy.get_requests(), data['filter'])
            response['requests'] = self.sluggifyRequests(self.server.proxy.get_requests())
            response['success'] = True
            response['zapi_result'] = zapi_result
        content = json.dumps(response)
        self.send_response(200)
        self.send_header("Content-type", "text/unknown")
        self.send_header("Content-Length", len(bytes(content, 'utf-8')))
        self.end_headers()
        self.wfile.write(bytes(content, 'utf-8'))
        return

    def do_GET(self):
        self.path = '/html/{}'.format(self.path)
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


class WebScenarioBuilderHttpServer(HTTPServer):
    def __init__(self, config):
        super().__init__(('localhost', config.getint('recording_api_port', 3129)), WebScenarioBuilderHttpRequestHandler)
        return

    def run(self, proxy, zapi):
        self.proxy = proxy
        self.zapi = zapi
        logging.info('Démarage du serveur d api')
        self.serve_forever()
        return
