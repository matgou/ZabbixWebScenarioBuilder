# -*- coding: utf-8 -*-
"""
main.py
~~~~~~~

Read mitmproxy flow output file and build a webservice call with it
"""
import asyncio
import configparser
import logging.config
import os
import sys
import threading
import time
import webbrowser

import janus as janus
import typing
from mitmproxy import http, exceptions, options, master, optmanager, proxy
from mitmproxy.tools._main import process_options
from mitmproxy.tools.main import cmdline, argparse
from mitmproxy.tools import dump
from mitmproxy.utils import arg_check

from http_api import WebScenarioBuilderHttpServer, WebScenarioBuilderWebsocket
from zabbix_client import ZabbixClientApi


class CaptiveProxyDumper(dump.DumpMaster):
    _instance = None

    def __new__(cls, opts, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = super(CaptiveProxyDumper, cls).__new__(cls, *args, **kwargs)
        return cls._instance

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
        r = flow.request
        self.requests.append(r)
        logging.info('{} {}://{}/{}'.format(r.method, r.scheme, r.host, r.path))
        self.queue.sync_q.put(r)


class BasicProxy():
    def activate_proxy(self):
        pass

    def desactivate_proxy(self):
        pass


class CaptiveProxy:
    """ =======================================================
     CaptiveProxy
     Start the Man-In-The-Middle Proxy
        ======================================================= """

    def __init__(self, config_ini):
        if os.name == 'nt':
            from proxy.win_local_proxy import WindowsProxy
            self.proxy_manager = WindowsProxy()
        else:
            self.proxy_manager = BasicProxy()
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

    def run(self,
            master_cls: typing.Type[master.Master],
            make_parser: typing.Callable[[options.Options], argparse.ArgumentParser],
            arguments: typing.Sequence[str],
            extra: typing.Callable[[typing.Any], dict] = None
    ) -> master.Master:  # pragma: no cover
        """
            extra: Extra argument processing callable which returns a dict of
            options.
        """
        opts = options.Options()
        master = master_cls(opts)

        parser = make_parser(opts)

        # To make migration from 2.x to 3.0 bearable.
        if "-R" in sys.argv and sys.argv[sys.argv.index("-R") + 1].startswith("http"):
            print("To use mitmproxy in reverse mode please use --mode reverse:SPEC instead")

        try:
            args = parser.parse_args(arguments)
        except SystemExit:
            arg_check.check()
            sys.exit(1)

        try:
            opts.set(*args.setoptions, defer=True)
            optmanager.load_paths(
                opts,
                os.path.join(opts.confdir, "config.yaml"),
                os.path.join(opts.confdir, "config.yml"),
            )
            pconf = process_options(parser, opts, args)
            server: typing.Any = None
            if pconf.options.server:
                try:
                    server = proxy.server.ProxyServer(pconf)
                except exceptions.ServerException as v:
                    print(str(v), file=sys.stderr)
                    sys.exit(1)
            else:
                server = proxy.server.DummyServer(pconf)

            master.server = server
            if args.options:
                print(optmanager.dump_defaults(opts))
                sys.exit(0)
            if args.commands:
                master.commands.dump()
                sys.exit(0)
            if extra:
                if (args.filter_args):
                    master.log.info(f"Only processing flows that match \"{' & '.join(args.filter_args)}\"")
                opts.update(**extra(args))

            loop = asyncio.get_event_loop()

            # Make sure that we catch KeyboardInterrupts on Windows.
            # https://stackoverflow.com/a/36925722/934719
            if os.name == "nt":
                async def wakeup():
                    while True:
                        await asyncio.sleep(0.2)

                asyncio.ensure_future(wakeup())

            master.run()
        except exceptions.OptionsError as e:
            print("%s: %s" % (sys.argv[0], e), file=sys.stderr)
            sys.exit(1)
        except (KeyboardInterrupt, RuntimeError):
            pass

    def start_proxy(self):
        """
        Start proxy
        :return:
        """
        logging.info('Démarage du serveur proxy sur 127.0.0.1:{}'.format(self.listen_port))
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        args = ['-p', str(self.listen_port)]

        def extra(args):
            if args.filter_args:
                v = " ".join(args.filter_args)
                return dict(
                    save_stream_filter=v,
                    readfile_filter=v,
                    dumper_filter=v,
                )
            return {}

        self.run(CaptiveProxyDumper, cmdline.mitmdump, args, extra)
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
    api_thread = threading.Thread(target=WebScenarioBuilderHttpServer.run, args=(api, proxy, zapi,))
    api_thread.daemon = True
    api_thread.start()
    webbrowser.open("http://127.0.0.1:{}".format(config['API']['recording_api_port']))

    """ Start websocket """
    api_websocket = WebScenarioBuilderWebsocket(config['API'], zapi)
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
