import json
import logging

from pyzabbix import ZabbixAPI, ZabbixAPIException


class ZabbixClientApi:
    def __init__(self):
        self.i=0

    def request_2_step(self, request):
        step = {
            'name': 'step {}'.format(i),
            'url': '{}://{}{}'.format(request.scheme, request.host, request.path),
            'no': self.i,
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
        self.i = self.i + 1
        return step

    def push(self, host_key, scenario_name, requests, filter):
        steps=[]
        i=0
        for request in requests:
            ignore_step = False
            for ext in self.zabbix_ignore_ext:
                if request.path.endswith(ext):
                    ignore_step = True
                if "{}?".format(ext) in request.path:
                    ignore_step = True
                if filter != "" and filter not in '{}://{}{}'.format(request.scheme, request.host, request.path):
                    ignore_step = True
            step = {
                'name': 'step {}'.format(i),
                'url': '{}://{}{}'.format(request.scheme, request.host, request.path),
                'no': i,
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
                            post_data_raw=request.text
                if post_data_raw == '':
                    step['posts'] = post_data
                #TODO voir pourquoi ca passe pas
                #else:
                #    step['post'] = post_data_raw
            if not ignore_step:
                logging.info('Step {} : {}'.format(i, json.dumps(step)))
                logging.info('Request data : {}'.format(request.text))
                steps.append(step)
            i = i + 1
        try:
            response=self.zapi.do_request('httptest.create', {'name': scenario_name, 'hostid': host_key, 'steps': steps})
        except ZabbixAPIException as err:
            response=str(err.error)
            return response

        return response['result']

    def __init__(self, config):
        self.config = config
        zabbix_host = config['zabbix_host']
        zabbix_user = config['zabbix_user']
        zabbix_password = config['zabbix_password']
        self.zabbix_ignore_ext = config['zabbix_ignore_ext'].split(',')

        # Create ZabbixAPI class instance
        logging.info('Connexion au serveur {}'.format(zabbix_host))
        self.zapi = ZabbixAPI(server=zabbix_host)
        self.zapi.login(zabbix_user, zabbix_password)

