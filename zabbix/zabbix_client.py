import base64
import json
import logging

from mitmproxy import http
from pyzabbix import ZabbixAPI, ZabbixAPIException


class ZabbixClientApi:

    def __init__(self):
        self.counter = 0

    def increaseCounter(self):
        if hasattr(self, 'counter'):
            self.counter = self.counter + 1
        else:
            self.counter = 0
        return self.counter

    def request_host(self, q):
        array = []
        hosts_result = self.zapi.do_request('host.get', {'search': {'name': '{}'.format(q)}})
        logging.debug('Zabbix host search result : {}'.format(hosts_result))
        for host in hosts_result['result']:
            array.append({'value': host['host'], 'id': host['hostid']})
        return array

    def request_template(self, q):
        array = []
        templates_result = self.zapi.do_request('template.get', {'search': {'name': '{}'.format(q)}})
        logging.debug('Zabbix template search result : {}'.format(templates_result))
        for host in templates_result['result']:
            array.append({'value': host['host'], 'id': host['templateid']})
        return array

    def request_2_step(self, f: http.HTTPFlow):
        request = f.request
        counter = self.increaseCounter()
        response_headers = []
        request_headers = []
        for key, value in f.response.headers.fields:
            response_headers.append({'name': key, 'value': value})
        # Filter to ignore some request header (like cookie, ...)
        for key, value in f.request.headers.fields:
            ignore_header_status = False

            for ignore_header in self.config['zabbix_ignore_header'].split(','):
                if str(key.decode('utf-8')).lower() == ignore_header.lower():
                    ignore_header_status = True
            if not ignore_header_status:
                request_headers.append({'name': key, 'value': value})
        step = {
            'name': 'step {}'.format(counter),
            'url': '{}://{}{}'.format(request.scheme, request.host, request.path),
            'no': counter,
            'headers': request_headers,
            'status_codes': str(f.response.status_code),
            'extra': {
                'method': request.method,
                'request_raw_data': request.text,
                'response': base64.b64encode(f.response.content),
                'status_code': f.response.status_code,
                'response_header': response_headers,
                'request_header': request_headers
            }
        }
        if request.method == 'POST':
            post_data = []
            post_data_raw = ''
            for d in request.text.split('&'):
                if d != '':
                    p = d.split('=')
                    if len(p) > 1:
                        field = {'name': p[0], 'value': p[1]}
                        post_data.append(field)
                    else:
                        post_data_raw = request.text
            if post_data_raw == '':
                step['posts'] = post_data
            # TODO voir pourquoi ca passe pas
            # else:
            #    step['post'] = post_data_raw
        logging.debug('We have converted transaction to step object : {}'.format(step))
        return step

    def push(self, host_key, scenario_name, requests, filter):
        steps = []
        i = 0
        for request in requests:
            step = request
            del step['extra']
            step['no'] = i
            # self.request_2_step(request)
            logging.info('Step {} : {}'.format(i, json.dumps(step)))
            steps.append(step)
            i = i + 1
        try:
            hosts_result = self.zapi.do_request('host.get', {'filter': {'name': '{}'.format(host_key)}})
            logging.debug(hosts_result['result'])
            logging.debug(len(hosts_result['result']))
            if len(hosts_result['result']) == 1:
                host_key = hosts_result['result'][0]['hostid']
            templates_result = self.zapi.do_request('template.get', {'filter': {'name': '{}'.format(host_key)}})
            logging.debug(templates_result)
            if len(templates_result['result']) == 1:
                host_key = templates_result['result'][0]['host']
            httptest_exist = self.zapi.do_request('httptest.get',
                                                  {'filter': {'name': scenario_name, 'hostid': host_key}})
            if len(httptest_exist['result']) == 1:
                response = self.zapi.do_request('httptest.update',
                                                {'httptestid': httptest_exist['result'][0]['httptestid'],
                                                 'step': steps})
            else:
                response = self.zapi.do_request('httptest.create',
                                                {'name': scenario_name, 'hostid': host_key, 'steps': steps})
            response = self.zapi.do_request('httptest.get', {'filter': {'name': scenario_name, 'hostid': host_key}})
            logging.debug('Zabbix httptest.create response : {}'.format(response))
        except ZabbixAPIException as err:
            response = str(err.error)
            return response

        return response['result']

    def __init__(self, config):
        self.config = config
        zabbix_host = config['zabbix_host']
        zabbix_user = config['zabbix_user']
        zabbix_password = config['zabbix_password']

        # Create ZabbixAPI class instance
        logging.info('Connexion au serveur {}'.format(zabbix_host))
        self.zapi = ZabbixAPI(server=zabbix_host)
        self.zapi.login(zabbix_user, zabbix_password)
