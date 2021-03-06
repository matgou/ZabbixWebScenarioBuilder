import asyncio
import functools
import http
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler

import simplejson as json
import websockets


async def echo(websocket, path):
    async for message in websocket:
        await websocket.send(message)


class WebScenarioBuilderWebsocket:
    def __init__(self, config, zapi):
        super().__init__()
        self.port = int(config['recording_api_websocket_port'])
        self.zapi = zapi
        self.connected = []

    async def sendAll(self, async_q):
        while True:
            f = await async_q.get()
            msg_obj = self.zapi.request_2_step(f)
            try:
                msg = json.dumps(msg_obj)
            except Exception as ex:
                msg_obj['extra'] = {}
                msg = json.dumps(msg_obj)
            logging.debug('Send "{}" to websocket ({} connected)'.format(msg, str(len(self.connected))))
            for ws in self.connected:
                try:
                    await ws.send(msg)
                except Exception as e:
                    logging.error(e)
                logging.debug(' => {}'.format(msg))
            async_q.task_done()

    async def recv(ws, path, self):
        self.connected.append(ws)
        name = await ws.recv()
        logging.debug('websocket recv: {}'.format(name))
        await ws.recv()

    def run(self):
        logging.info('Start websocket server : localhost:{}'.format(str(self.port)))
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bound_handler = functools.partial(WebScenarioBuilderWebsocket.recv, self=self)
        start_server = websockets.serve(bound_handler, 'localhost', self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()


class WebScenarioBuilderHttpRequestHandler(SimpleHTTPRequestHandler):
    def sluggifyRequests(self, requests):
        r = []
        for request in requests:
            r.append(self.server.zapi.request_2_step(request))
        return r

    def do_POST(self):
        response = {'success': False, 'requests': []}
        if self.path == '/start_recording':
            self.server.proxy.start_recording()
            response['success'] = True
        if self.path == '/stop_recording':
            self.server.proxy.stop_recording()
            response['success'] = True
        if self.path == '/push_zabbix':
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))
            data = json.loads(self.data_string)
            if not 'filter' in data:
                data['filter'] = ""
            zapi_result = self.server.zapi.push(data['host_key'], data['scenario_name'],
                                                data['requests'], data['filter'])
            response['success'] = True
            response['zapi_host'] = self.server.zapi.config['zabbix_host']
            response['zapi_result'] = zapi_result
        content = json.dumps(response)
        self.send_response(200)
        self.send_header("Content-type", "text/unknown")
        self.send_header("Content-Length", len(bytes(content, 'utf-8')))
        self.end_headers()
        self.wfile.write(bytes(content, 'utf-8'))
        return

    def do_GET(self):
        if self.path.startswith('/zabbix_host?q='):
            q = self.path[len('/zabbix_host?q='):]
            response = self.server.zapi.request_host(q) + self.server.zapi.request_template(q)
            content = json.dumps(response)
            self.send_response(200)
            self.send_header("Content-type", "text/unknown")
            self.send_header("Content-Length", len(bytes(content, 'utf-8')))
            self.end_headers()
            self.wfile.write(bytes(content, 'utf-8'))
            return
        else:
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
