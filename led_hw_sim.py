#!./venv/bin/python
import asyncio
from logging import debug, info

import numpy as np
import pygame
import pygame.locals

from led_hw_any import LED_HW_Any


class HW_PyGame(LED_HW_Any):
    loop: asyncio.AbstractEventLoop
    scale: int
    cmdq: asyncio.Queue
    window: pygame.Surface
    evt_consumer: asyncio.Task

    __slots__ = ['loop', 'scale', 'cmdq', 'window', 'evt_consumer']

    def __init__(self, loop: asyncio.AbstractEventLoop, width: int, height: int,
                 scale: int, cmdq: asyncio.Queue[str]):
        super().__init__(width, height)
        self.loop = loop
        self.scale = scale
        self.cmdq = cmdq

        pygame.init()
        self.window = pygame.display.set_mode(
            (scale * self.width + 1, scale * self.height + 1))
        self.evt_consumer = loop.create_task(self._evt_consumer_coro())

    # stop the 'HW'
    def stop(self):
        self.running = False
        pygame.quit()

    async def _evt_consumer_coro(self):
        while self.running:
            if not pygame.event.peek():
                await asyncio.sleep(0.1)
                continue
            event = pygame.event.poll()
            debug(f'pygame Event {repr(event)} received.')
            if event.type == pygame.locals.QUIT:
                info('Window has been closed, exiting.')
                self.running = False
            elif event.type == pygame.locals.KEYUP:
                if event.key == pygame.locals.K_ESCAPE:
                    info('ESC has been presed, exiting.')
                    self.running = False
                if event.key == pygame.locals.K_o:
                    self.cmdq.put_nowait('o_released')
                if event.key == pygame.locals.K_i:
                    self.cmdq.put_nowait('i_released')
            elif event.type == pygame.locals.KEYDOWN:
                if event.key == pygame.locals.K_o:
                    self.cmdq.put_nowait('o_pressed')
                if event.key == pygame.locals.K_i:
                    self.cmdq.put_nowait('i_pressed')

    # update pixel matrix from PIL Image
    def update(self, img: np.ndarray):
        assert img.ndim == 3
        assert img.shape == (self.height, self.width, 3)
        assert img.dtype == np.uint8

        rect = pygame.Rect(0, 0, self.scale * self.width + 1,
                           self.scale * self.height + 1)
        pygame.draw.rect(self.window, (0x10, 0x10, 0x10), rect)

        for y, x in np.ndindex(img.shape[0:2]):
            rect = pygame.Rect(x * self.scale + 1, y * self.scale + 1,
                               self.scale - 1, self.scale - 1)
            pygame.draw.rect(self.window, img[y, x], rect)

        pygame.display.flip()
