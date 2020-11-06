# -*- coding: utf-8 -*-
"""
main.py
~~~~~~~

Read mitmproxy flow output file and build a webservice call with it
"""
import asyncio
import configparser
import json
import logging.config
import sys
import threading
import time
import webbrowser
from functools import wraps, partial

import janus as janus
from mitmproxy import http
from mitmproxy.tools.main import mitmdump, cmdline, run
from mitmproxy.tools import dump

from http_api import WebScenarioBuilderHttpServer, WebScenarioBuilderWebsocket
from local_proxy import WindowsProxy
from zabbix_client import ZabbixClientApi

class CaptiveProxyDumper(dump.DumpMaster):
    _instance = None

    def __new__(class_, opts,*args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = super(CaptiveProxyDumper, class_).__new__(class_, *args, **kwargs)
        return class_._instance

    def __init__(self, opts):
        super().__init__(opts)
        self.addonCaptive = CaptiveProxyAddon()
        self.addons.add(self.addonCaptive)
        self.addons.remove(self.addons.get('termlog'))
        self.addons.remove(self.addons.get('dumper'))


class CaptiveProxyAddon():
    def __init__(self):
        self.requests = []
        self.websocket = None
        self.queue = None
        self.zapi = None

    async def set_websocket(self, ws):
        self.websocket = ws
        self.queue = janus.Queue()
        await ws.sendAll(self.queue.async_q)

    def request(self, flow: http.HTTPFlow) -> None:
        r=flow.request
        self.requests.append(r)
        logging.info('{} {}://{}/{}'.format(r.method, r.scheme, r.host, r.path))
        self.queue.sync_q.put(r)

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
        CaptiveProxyDumper._instance.addonCaptive.requests = []
        return;

    def get_requests(self):
        return CaptiveProxyDumper._instance.addonCaptive.requests

    def stop_recording(self):
        try:
            self.proxy_manager.desactivate_proxy()
        except Exception:
            logging.error('Error when desactive proxy')
        time.sleep(1)
        return CaptiveProxyDumper._instance.addonCaptive.requests

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

    async def set_websocket(self, api_websocket):
        await CaptiveProxyDumper._instance.addonCaptive.set_websocket(api_websocket)

async def main():
    """ =======================================================
     Main function
        ======================================================= """
    logging.config.fileConfig('logging.conf')
    logging.info('Demarage du programme ZabbixWebScenarioBuilder (v1.0.0)')

    logging.debug('Chargement de la configuration depuis config.ini')
    config = configparser.ConfigParser()
    config.read('config.ini')

    """ Start the proxy and wait 1s for starting time """
    proxy = CaptiveProxy(config['PROXY'])
    proxy_thread = threading.Thread(target=CaptiveProxy.start_proxy, args=(proxy,))
    proxy_thread.daemon = True
    proxy_thread.start()
    time.sleep(1)
    proxy.server = CaptiveProxyDumper._instance

    """ Zabbix API """
    zapi = ZabbixClientApi(config['ZABBIX'])

    """ Start rest api """
    api = WebScenarioBuilderHttpServer(config['API'])
    api_thread = threading.Thread(target=WebScenarioBuilderHttpServer.run, args=(api,proxy,zapi,))
    api_thread.daemon = True
    api_thread.start()
    webbrowser.open("http://127.0.0.1:{}".format(config['API']['recording_api_port']))

    """ Start websocket """
    api_websocket = WebScenarioBuilderWebsocket(config['API'])
    websocket_thread = threading.Thread(target=WebScenarioBuilderWebsocket.run, args=(api_websocket,))
    websocket_thread.daemon = True
    websocket_thread.start()
    await proxy.set_websocket(api_websocket)

    """ Record flow """
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
       True

    """ End of bash """
    logging.info('End of bash')
    proxy.stop_proxy()
    sys.exit(0)

""" Main entrypoint """
if __name__ == '__main__':
    asyncio.run(main())
