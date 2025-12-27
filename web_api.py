#!/usr/bin/python
import asyncio
import json
import logging

from aiohttp import web

from led_sign import LEDSign


class LEDCylinderWebApi:
    sign: LEDSign
    log: logging.Logger

    __slots__ = ['sign', 'log']

    async def handle_http_status(self, req: web.Request) -> web.Response:
        self.log.info('Serving request {req}...')
        ret = {
            'page': self.sign.page_ix,
            'output': self.sign.output_active,
            'flash': self.sign.flash_active
        }
        return web.Response(status=200, body=json.dumps(ret), content_type='application/json')

    async def handle_http_power_on(self, req: web.Request) -> web.Response:
        self.sign.output_active = True
        return web.Response(status=200, text='ok')

    async def handle_http_power_off(self, req: web.Request) -> web.Response:
        self.sign.output_active = False
        return web.Response(status=200, text='ok')

    async def handle_http_flash_on(self, req: web.Request) -> web.Response:
        self.sign.flash_active = True
        return web.Response(status=200, text='ok')

    async def handle_http_flash_off(self, req: web.Request) -> web.Response:
        self.sign.flash_active = False
        return web.Response(status=200, text='ok')

    def __init__(self, loop: asyncio.AbstractEventLoop, sign: LEDSign, port: int):
        self.sign = sign

        self.log = logging.getLogger(__name__)
        self.log.info(f'Running webserver on port {port}.')

        app = web.Application()
        app.add_routes([
            web.get('/', self.handle_http_status),
            web.get('/output_on', self.handle_http_power_on),
            web.get('/output_off', self.handle_http_power_off),
            web.get('/flash_on', self.handle_http_flash_on),
            web.get('/flash_off', self.handle_http_flash_off),
        ])

        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())

        site = web.TCPSite(runner, '0.0.0.0', port)
        loop.run_until_complete(site.start())
