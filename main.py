# -*- coding: utf-8 -*-
"""
main.py
~~~~~~~

Read mitmproxy flow output file and build a webservice call with it
"""
import asyncio
import configparser
import logging.config
import sys
import threading
import time

from mitmproxy import http
from mitmproxy.tools.main import mitmdump, cmdline, run
from mitmproxy.tools import dump
from local_proxy import WindowsProxy

requests=[]

class CaptiveProxyDumper(dump.DumpMaster):
    _instance = None

    def __new__(class_, opts,*args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = super(CaptiveProxyDumper, class_).__new__(class_, *args, **kwargs)
        return class_._instance

    def __init__(self, opts):
        super().__init__(opts)
        self.addons.add(CaptiveProxyAddon())
        self.addons.remove(self.addons.get('termlog'))
        self.addons.remove(self.addons.get('dumper'))

class CaptiveProxyAddon():
    def request(self, flow: http.HTTPFlow) -> None:
        r=flow.request
        requests.append(r)
        logging.info('{} {}://{}/{}'.format(r.method, r.scheme, r.host, r.path))

class CaptiveProxy:
    """ =======================================================
     CaptiveProxy
     Start the Man-In-The-Middle Proxy
        ======================================================= """
    def __init__(self, config_ini):
        self.proxy_manager = WindowsProxy()
        self.config_ini = config_ini
        self.server = None
        self.listen_port = self.config_ini.getint('port', 3128)

    def start_recording(self):
        self.proxy_manager.activate_proxy()
        return;

    def stop_recording(self):
        self.proxy_manager.desactivate_proxy()
        time.sleep(2)
        return;

    def stop_proxy(self):
        """
        Stop proxy by sending shutdown to mitmproxy
        :return:
        """
        self.server.shutdown()
        return;

    def start_proxy(self):
        """
        Start proxy
        :return:
        """
        logging.info('Démarage du serveur proxy sur 127.0.0.1:{}'.format(self.listen_port))
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        args=['-p', str(self.listen_port)]

        def extra(args):
            if args.filter_args:
                v = " ".join(args.filter_args)
                return dict(
                    save_stream_filter=v,
                    readfile_filter=v,
                    dumper_filter=v,
                )
            return {}

        run(CaptiveProxyDumper, cmdline.mitmdump, args, extra)
        return;


def main():
    """ =======================================================
     Main function
        ======================================================= """
    logging.config.fileConfig('logging.conf')
    logging.info('Demarage du programme ZabbixWebScenarioBuilder (v1.0.0)')

    logging.debug('Chargement de la configuration depuis config.ini')
    config = configparser.ConfigParser()
    config.read('config.ini')

    """ Start the proxy and wait 5s for skype """
    proxy = CaptiveProxy(config['PROXY'])
    proxy_thread = threading.Thread(target=CaptiveProxy.start_proxy, args=(proxy,))
    proxy_thread.daemon = True
    proxy_thread.start()
    time.sleep(1)
    proxy.server = CaptiveProxyDumper._instance

    """ Parsing des arguments """
    scenario_name = None
    if len(sys.argv) > 1:
        scenario_name = sys.argv[1]
    #else:
    #    scenario_name = input("Enter zabbix scenario name to create/update:")
    logging.info("Using scenario name : {}".format(scenario_name))

    """ Record flow """
    logging.info('Start recording via captive proxy')
    proxy.start_recording()
    try:
        time.sleep(config['DEFAULT'].getint('recording_timeout', 300))
    except KeyboardInterrupt:
        logging.info('End of capture')
    proxy.stop_recording()
    logging.info('Stop recording via captive proxy')

    """ Generate zabbix httptest """
    print(requests)

    """ End of bash """
    logging.info('End of bash')
    proxy.stop_proxy()
    sys.exit(0)

""" Main entrypoint """
if __name__ == '__main__':
    main()
