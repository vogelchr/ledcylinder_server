#!/usr/bin/env ./.venv/bin/python

import argparse
import asyncio
import logging
from logging import info
from pathlib import Path
from typing import List

import PIL.Image
import numpy as np

from led_layer import LED_Layer


async def mainloop(args: argparse.Namespace, layers: List[LED_Layer], hw):
    layer_ix = 0
    dt_remain = args.page_time
    dt_secs = 1.0 / args.fps

    while hw.running:
        if type(layer_ix) == tuple:
            ix_a, ix_b = layer_ix
            layers[ix_a].tick(dt_secs)
            layers[ix_b].tick(dt_secs)

            ndarr_a = np.array(layers[ix_a].get())  # numpy array
            ndarr_b = np.array(layers[ix_b].get())

            fade = dt_remain / args.fade_time

            ndarr_combine = np.clip(
                np.power(fade, 3) * ndarr_a + np.power(1.0 - fade, 3) * ndarr_b, 0, 255).astype(np.uint8)
            img = PIL.Image.fromarray(ndarr_combine, 'RGB')
        else:
            layers[layer_ix].tick(dt_secs)
            img = layers[layer_ix].get()

        hw.update(img)

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
    grp.add_argument('-l', '--limit-brightness', type=int, choices=range(1, 256),
                     default=255, help='Limit brightness of individual pages [def:%(default)d]')

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

    if len(args.layers) == 1 and args.layers[0].is_dir():
        args.layers = sorted(args.layers[0].glob('*'))

    info('Loading layers.')
    layers = list()
    for fn in args.layers:
        layer = LED_Layer.from_file(fn, args.limit_brightness)
        if layer is None:
            continue
        assert layer.width == args.width
        assert layer.height == args.height
        layers.append(layer)

    if args.simulation:
        info('Starting pygame simulator hardware...')
        from led_hw_sim import HW_PyGame
        hw = HW_PyGame(loop, args.width, args.height)
    else:
        info('Running with real USB hardware...')
        from led_hw_usb import HW_USB
        hw = HW_USB()
    try:
        info('Starting mainloop..')
        loop.run_until_complete(mainloop(args, layers, hw))
    except KeyboardInterrupt:
        if args.simulation:
            hw.stop()


if __name__ == '__main__':
    main()
