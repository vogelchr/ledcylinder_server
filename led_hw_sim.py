#!./venv/bin/python
import asyncio
from logging import critical, debug, error, info, warning

import PIL.Image
import pygame
import pygame.locals


class HW_PyGame:
    def __init__(self, loop, width, height):
        self.loop = loop
        self.width, self.height = width, height
        self.running = True

        pygame.init()
        self.window = pygame.display.set_mode(
            (3*self.width+1, 3*self.height+1))
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
            if event.type == pygame.locals.KEYUP and event.key == pygame.locals.K_ESCAPE:
                info('ESC has been presed, exiting.')
                self.running = False

    # update pixel matrix from PIL Image
    def update(self, img: PIL.Image):
        assert img.mode == 'RGB'

        rect = pygame.Rect(0, 0, 3*self.width+1, 3*self.height+1)
        pygame.draw.rect(self.window, (0x10, 0x10, 0x10), rect)

        # this is very, very inefficient
        for x in range(min(self.width, img.size[0])):
            for y in range(min(self.height, img.size[1])):
                rect = pygame.Rect(x*3+1, y*3+1, 2, 2)
                pygame.draw.rect(self.window, img.getpixel((x, y)), rect)

        pygame.display.flip()
