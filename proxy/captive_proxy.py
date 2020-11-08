import argparse
import asyncio
import logging
import os
import sys
import time
import typing

import janus as janus
from mitmproxy import http, master, options, optmanager, proxy, exceptions
from mitmproxy.tools import dump, cmdline
from mitmproxy.tools.main import process_options
from mitmproxy.utils import arg_check


class BasicProxy():
    def activate_proxy(self):
        pass

    def desactivate_proxy(self):
        pass


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

    @property
    def instance(self):
        return self._instance


class CaptiveProxyAddon():
    def __init__(self):
        self.requests = []
        self.websocket = None
        self.queue = None
        self.zapi = None
        self.proxy_ignore_ext = []

    async def set_config(self, config):
        logging.info('fix config')
        self.config = config
        self.proxy_ignore_ext = config['PROXY']['proxy_ignore_ext'].split(',')

    async def set_websocket(self, ws):
        self.websocket = ws
        self.queue = janus.Queue()
        await ws.sendAll(self.queue.async_q)

    def response(self, flow: http.HTTPFlow) -> None:
        r = flow.request
        ignore_step = False
        for ext in self.proxy_ignore_ext:
            if r.path.endswith(ext):
                ignore_step = True
            if "{}?".format(ext) in r.path:
                ignore_step = True
        if not ignore_step:
            self.requests.append(r)
            logging.info('{} {}://{}/{}'.format(r.method, r.scheme, r.host, r.path))
            self.queue.sync_q.put(flow)


class CaptiveProxy:
    """ =======================================================
     CaptiveProxy
     Start the Man-In-The-Middle Proxy
        ======================================================= """

    def __init__(self, config_ini):
        if os.name == 'nt':
            from proxy.win_local_proxy_switcher import WindowsProxy
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

    async def set_config(self, config):
        await CaptiveProxyDumper._instance.addonCaptive.set_config(config)
