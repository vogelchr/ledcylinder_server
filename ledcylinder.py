#!/usr/bin/env ./.venv/bin/python

import argparse
import asyncio
import logging
from logging import info
from pathlib import Path
from typing import List

import PIL.Image
import numpy as np

from led_hw_sim import HW_PyGame
from led_layer import LED_Layer


def _rotate(src: PIL.Image.Image, xoffs: int):
    width, height = src.size
    ret = PIL.Image.new('RGB', src.size)

    src_left = src.crop((0, 0, width - xoffs, height))
    ret.paste(src_left, (xoffs, 0))

    if xoffs > 0:
        src_right = src.crop((width - xoffs, 0, width, height))
        ret.paste(src_right, (0, 0))

    return ret


async def mainloop(args: argparse.Namespace, layers: List[LED_Layer], hw: HW_PyGame):
    x_offset = 0

    layer_ix = 0
    dt_remain = args.page_time
    dt_secs = 1.0 / args.fps

    while hw.running:
        if type(layer_ix) == tuple:
            ix_a, ix_b = layer_ix
            layers[ix_a].tick()
            layers[ix_b].tick()

            ndarr_a = np.array(layers[ix_a].get())  # numpy array
            ndarr_b = np.array(layers[ix_b].get())

            fade = dt_remain / args.fade_time

            ndarr_combine = np.clip(
                fade * ndarr_a + (1.0 - fade) * ndarr_b, 0, 255).astype(np.uint8)
            img = PIL.Image.fromarray(ndarr_combine, 'RGB')
        else:
            layers[layer_ix].tick()
            img = layers[layer_ix].get()

        hw.update(_rotate(img, x_offset))

        x_offset -= 1
        if x_offset >= hw.width:
            x_offset = 0
        if x_offset < 0:
            x_offset = hw.width - 1

        dt_remain -= dt_secs
        if dt_remain < 0:
            if type(layer_ix) == tuple:
                layer_ix = layer_ix[1]
                dt_remain = args.page_time
            else:
                ix_b = layer_ix + 1
                if ix_b >= len(layers):
                    ix_b = 0
                layer_ix = (layer_ix, ix_b)
                dt_remain = args.fade_time
            print('Switching to layer', layer_ix)
        await asyncio.sleep(dt_secs)


def main():
    parser = argparse.ArgumentParser()

    grp = parser.add_argument_group('Logging')

    grp.add_argument('-q', '--quiet', action='store_true',
                     help='Be quiet (logging level: warning)')
    grp.add_argument('-v', '--verbose', action='store_true',
                     help='Be verbose (logging level: debug)')

    grp = parser.add_argument_group('Hardware')

    grp.add_argument('-W', '--width', type=int, default=128,
                     help='LED panel width [def:%(default)d]')
    grp.add_argument('-H', '--height', type=int, default=8,
                     help='LED panel height [def:%(default)d]')

    grp.add_argument('-S', '--simulation', action='store_true',
                     help='Simulate with pyGame')

    grp = parser.add_argument_group('Rendering')

    grp.add_argument('-F', '--fps', type=float, metavar='Hz', default=60,
                     help='Frames per Second (approx) [def:%(default).1f]')
    grp.add_argument('-p', '--page-time', metavar='sec', default=5.0,
                     help='Switch pages after sec seconds [def:%(default).1f]')
    grp.add_argument('-f', '--fade-time', metavar='sec', default=1.0,
                     help='Switch pages after sec seconds [def:%(default).1f]')

    parser.add_argument('layers', type=Path, nargs='+')

    args = parser.parse_args()

    # confiure logging
    log_lvl = logging.INFO
    if args.verbose:
        log_lvl = logging.DEBUG
    if args.quiet:
        log_lvl = logging.WARNING

    logging.basicConfig(level=log_lvl, format='%(asctime)s %(message)s')
    loop = asyncio.new_event_loop()

    info('Loading layers.')
    layers = list()
    for fn in args.layers:
        layer = LED_Layer.from_file(fn)
        assert layer.width == args.width
        assert layer.height == args.height
        layers.append(layer)

    info('Starting pygame simulator hardware...')
    hw = HW_PyGame(loop, args.width, args.height)

    try:
        info('Starting mainloop..')
        loop.run_until_complete(mainloop(args, layers, hw))
    except KeyboardInterrupt:
        hw.stop()


if __name__ == '__main__':
    main()
