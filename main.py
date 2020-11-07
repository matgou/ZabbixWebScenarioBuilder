# -*- coding: utf-8 -*-
"""
main.py
~~~~~~~

Start mitmproxy and a EDI in navigator to capture webtraffic and export request to zabbix
"""
import asyncio
import configparser
import logging.config
import sys
import threading
import time
import webbrowser

from webserver.http_api import WebScenarioBuilderHttpServer, WebScenarioBuilderWebsocket
from proxy.captive_proxy import CaptiveProxyDumper, CaptiveProxy
from zabbix.zabbix_client import ZabbixClientApi


async def main():
    """ =======================================================
     Main function
        ======================================================= """
    logging.config.fileConfig('logging.conf')
    logging.info('Start ZabbixWebScenarioBuilder (v1.0.0)')

    logging.debug('Load config from config.ini')
    config = configparser.ConfigParser()
    config.read('config.ini')

    """ Start the proxy and wait 1s for starting time """
    proxy = CaptiveProxy(config['PROXY'])
    proxy_thread = threading.Thread(target=CaptiveProxy.start_proxy, args=(proxy,))
    proxy_thread.daemon = True
    proxy_thread.start()
    time.sleep(1)
    await proxy.set_config(config)
    proxy.server = CaptiveProxyDumper.instance

    """ Zabbix API """
    zapi = ZabbixClientApi(config['ZABBIX'])

    """ Start rest api """
    api = WebScenarioBuilderHttpServer(config['API'])
    api_thread = threading.Thread(target=WebScenarioBuilderHttpServer.run, args=(api, proxy, zapi,))
    api_thread.daemon = True
    api_thread.start()
    webbrowser.open("http://127.0.0.1:{}".format(config['API']['recording_api_port']))

    """ Start websocket """
    api_websockets = WebScenarioBuilderWebsocket(config['API'], zapi)
    websockets_thread = threading.Thread(target=WebScenarioBuilderWebsocket.run, args=(api_websockets,))
    websockets_thread.daemon = True
    websockets_thread.start()
    await proxy.set_websocket(api_websockets)

    """ Record flow """
    try:
        while True:
            asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    """ End of bash """
    logging.info('End of bash')
    proxy.stop_proxy()
    sys.exit(0)


""" Main entrypoint """
if __name__ == '__main__':
    asyncio.run(main())
