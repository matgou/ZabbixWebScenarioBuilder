
# -*- coding: utf-8 -*-
"""
main.py
~~~~~~~

Read mitmproxy flow output file and build a webservice call with it
"""

import json, sys
from mitmproxy import io
from mitmproxy.exceptions import FlowReadException
from pyzabbix import ZabbixAPI
import configparser
import logging.config

if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    logging.info('Demarage du programme de conversion mitmproxy2zabbix')
    mitmproxy_dump=sys.argv[1]
    scenario_name=sys.argv[2]

    logging.debug('Chargement de la configuration depuis config.ini')
    config=configparser.ConfigParser()
    config.read('config.ini')

    zabbix_host=config['DEFAULT']['zabbix_host']
    zabbix_user=config['DEFAULT']['zabbix_user']
    zabbix_password=config['DEFAULT']['zabbix_password']
    zabbix_hostid=config['DEFAULT']['zabbix_hostid']
    zabbix_ignore_ext=config['DEFAULT']['zabbix_ignore_ext'].split(',')

    # Create ZabbixAPI class instance
    logging.info('Connexion au serveur {}'.format(zabbix_host))
    zapi = ZabbixAPI(server=zabbix_host)
    zapi.login(zabbix_user, zabbix_password)

    logging.info('Read mitmproxy dump file : {}'.format(mitmproxy_dump))
    with open(mitmproxy_dump, "rb") as logfile:
        freader = io.FlowReader(logfile)
        try:
            i=1
            steps=[]
            for f in freader.stream():
                ignore_step=False
                request = f.request
                for ext in zabbix_ignore_ext:
                    if request.path.endswith(ext):
                        ignore_step=True
                response = f.response
                logging.debug('{} {}/{}'.format(request.method, request.host, request.path))
                step={
                  'name': 'step {}'.format(i),
                  'url': '{}://{}{}'.format(request.scheme, request.host, request.path),
                  'no': i,
                }
                if request.method == 'POST':
                    post_data=[]
                    for d in request.text.split('&'):
                        if d != '':
                            p=d.split('=')
                            field={'name': p[0], 'value': p[1]}
                            post_data.append(field)
                    step['posts']=post_data

                if ignore_step == False:
                    logging.info('Step {} : {}'.format(i,json.dumps(step)))
                    steps.append(step)
                i=i+1
        except FlowReadException as v:
            print("Flow file corrupted. Stopped loading.")

    logging.info('Create Webscenario in zabbix')
    zapi.do_request('httptest.create',{'name': scenario_name, 'hostid': zabbix_hostid, 'steps': steps})
    logging.info('End of bash')