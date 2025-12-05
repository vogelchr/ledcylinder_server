import asyncio
import logging
import random
from typing import Union, Tuple, List

import numpy as np

from led_hw_sim import HW_PyGame
from led_hw_usb import HW_USB
from led_page import LEDPage

logger = logging.getLogger(__name__)


class LEDSign:
    hw: Union[HW_USB, HW_PyGame]
    pages: List[LEDPage]

    page_ix: Union[Tuple[int, int], int]
    page_time: float
    fade_time: float
    dt_remain: float
    dt_secs: float

    randomize_pages: bool
    output_active: bool
    flash_active: bool

    cmdq: asyncio.Queue

    all_white_img: np.ndarray
    all_black_img: np.ndarray
    fade_img: np.ndarray
    fade_tmp: np.ndarray

    __slots__ = ['hw', 'pages', 'page_ix', 'page_time', 'fade_time',
                 'dt_remain', 'dt_secs', 'randomize_pages', 'output_active',
                 'flash_active', 'cmdq', 'all_white_img', 'all_black_img',
                 'fade_img', 'fade_tmp', ]

    def __init__(self, hw: Union[HW_USB, HW_PyGame], page_time: float,
                 fade_time: float, fps: float, cmdq: asyncio.Queue,
                 randomize_pages: bool):
        self.hw = hw
        self.pages = []

        self.page_ix = 0
        self.page_time = page_time
        self.fade_time = fade_time
        self.dt_remain = page_time
        self.dt_secs = 1.0 / fps

        self.randomize_pages = randomize_pages
        self.output_active = True
        self.flash_active = False

        self.cmdq = cmdq

        self.all_white_img = np.full((hw.height, hw.width, 3), 0xff,
                                     dtype=np.uint8)
        self.all_black_img = np.full((hw.height, hw.width, 3), 0x00,
                                     dtype=np.uint8)

        # avoid too many object creations/deletions
        self.fade_img = np.zeros((hw.height, hw.width, 3), dtype='f')
        self.fade_tmp = np.zeros((hw.height, hw.width, 3), dtype='f')

    def add_page(self, page: LEDPage):
        self.pages.append(page)

    async def mainloop(self):
        while self.hw.running:
            if not self.cmdq.empty():
                cmd = self.cmdq.get_nowait()

                if cmd == 'i_pressed':
                    logger.info('Blitzdings on!')
                    flash_active = True
                elif cmd == 'i_released':
                    logger.info('Blitzdings off!')
                    flash_active = False
                elif cmd == 'o_pressed':
                    self.output_active = not self.output_active
                    if self.output_active:
                        logger.info('Normal output.')
                    else:
                        logger.info('Blackout!')

            if type(self.page_ix) == tuple:
                ix_a, ix_b = self.page_ix
                self.pages[ix_a].tick(self.dt_secs)
                self.pages[ix_b].tick(self.dt_secs)

                fade = self.dt_remain / self.fade_time

                # try to avoid creation of too many tmp arrays
                self.fade_img[...] = self.pages[ix_a].get()
                self.fade_img *= np.power(fade, 3)

                self.fade_tmp[...] = self.pages[ix_b].get()
                self.fade_tmp *= np.power(1 - fade, 3)
                self.fade_img += self.fade_tmp

                self.fade_img = np.clip(self.fade_img, 0, 255)

                img = self.fade_img.astype(np.uint8)

            elif type(self.page_ix) == int:
                self.pages[self.page_ix].tick(self.dt_secs)
                img = self.pages[self.page_ix].get()
            else:
                raise RuntimeError(
                    'Fatal error, laxer ix neither tuple nor integer!')

            if self.flash_active:
                self.hw.update(self.all_white_img)
            else:
                if self.output_active:
                    self.hw.update(img)
                else:
                    self.hw.update(self.all_black_img)

            self.dt_remain -= self.dt_secs
            if self.dt_remain < 0:
                if len(self.pages) == 1:
                    # only one page, nothing to do
                    pass
                elif type(self.page_ix) == tuple:
                    self.page_ix = self.page_ix[1]
                    self.dt_remain = self.page_time
                elif type(self.page_ix) == int:
                    if self.randomize_pages:
                        # random page, but not the currently displayed
                        # one
                        ix_b = random.randint(0, len(self.pages) - 2)
                        if ix_b >= self.page_ix:
                            ix_b += 1
                    else:
                        ix_b = self.page_ix + 1
                        if ix_b >= len(self.pages):
                            ix_b = 0

                    self.pages[ix_b].x_increment = -1
                    self.page_ix = (self.page_ix, ix_b)
                    self.dt_remain = self.fade_time
                else:
                    raise RuntimeError(
                        'Fatal error, laxer ix neither tuple nor integer!')

            await asyncio.sleep(self.dt_secs)
