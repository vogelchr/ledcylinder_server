#!/usr/bin/env ./.venv/bin/python

import argparse
import asyncio
import logging
import random
from logging import info, exception
from pathlib import Path
from typing import List

import PIL.Image
import evdev
import evdev.ecodes
import numpy as np

from led_layer import LED_Layer


async def keyboard_task(keydev: evdev.InputDevice):
    key_pressed = dict()

    keydev.grab()
    async for evt in keydev.async_read_loop():
        evt: evdev.InputEvent

        if evt.type != evdev.ecodes.EV_KEY:
            # info(f'Not EV_KEY event: {evt}.')
            continue

        keyname = None
        if evt.code == evdev.ecodes.KEY_O:
            keyname = 'o'
        elif evt.code == evdev.ecodes.KEY_I:
            keyname = 'i'

        if keyname is None:
            # info(f'Key not I or O.')
            continue

        info(f'{keyname} {evt.value}')

        if evt.value and not key_pressed.get(keyname):
            key_pressed[keyname] = 1
            keyname += '_pressed'
        elif not evt.value and key_pressed.get(keyname):
            key_pressed[keyname] = 0
            keyname += '_released'
        else:
            keyname = None

        if not keyname:
            continue

        info(f'Key processing: {keyname}.')


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

            ndarr_combine = np.clip(np.power(fade, 3) * ndarr_a + np.power(1.0 - fade, 3) * ndarr_b, 0, 255).astype(
                np.uint8)
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
                if args.randomize_pages:
                    # random page, but not the currently displayed
                    # one
                    ix_b = random.randint(0, len(layers) - 2)
                    if ix_b >= layer_ix:
                        ix_b += 1
                else:
                    ix_b = layer_ix + 1
                    if ix_b >= len(layers):
                        ix_b = 0

                # this looks shitty
                #                layers[ix_b].x_increment = np.random.uniform(-1.1, -0.66)
                layers[ix_b].x_increment = -1
                layer_ix = (layer_ix, ix_b)
                dt_remain = args.fade_time
        await asyncio.sleep(dt_secs)


def main():
    parser = argparse.ArgumentParser()

    grp = parser.add_argument_group('Logging')

    grp.add_argument('-q', '--quiet', action='store_true', help='Be quiet (logging level: warning)')
    grp.add_argument('-v', '--verbose', action='store_true', help='Be verbose (logging level: debug)')

    grp = parser.add_argument_group('Hardware')

    grp.add_argument('-W', '--width', type=int, default=128, help='LED panel width [def:%(default)d]')
    grp.add_argument('-H', '--height', type=int, default=8, help='LED panel height [def:%(default)d]')

    grp.add_argument('-S', '--simulation', action='store_true', help='Simulate with pyGame')

    grp = parser.add_argument_group('Rendering')

    grp.add_argument('-F', '--fps', type=float, metavar='Hz', default=60,
                     help='Frames per Second (approx) [def:%(default).1f]')
    grp.add_argument('-p', '--page-time', type=float, metavar='sec', default=5.0,
                     help='Switch pages after sec seconds [def:%(default).1f]')
    grp.add_argument('-f', '--fade-time', type=float, metavar='sec', default=1.0,
                     help='Switch pages after sec seconds [def:%(default).1f]')
    grp.add_argument('-l', '--limit-brightness', type=int, default=255,
                     help='Limit brightness of individual pages [def:%(default)d]')
    grp.add_argument('-r', '--randomize-pages', action='store_true', help='Randomize order of pages.')

    grp.add_argument('-e', '--evdev', type=Path, help='Support button for flash, use /dev/input/eventXX')

    parser.add_argument('layers', type=Path, nargs='+')

    args = parser.parse_args()

    if args.limit_brightness < 1 or args.limit_brightness > 255:
        print('Error: Brightness limit cannot be <1 or >255!')

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
        try:
            layer = LED_Layer.from_file(fn, args.limit_brightness)
            if layer is None:
                continue
            assert layer.width == args.width
            assert layer.height == args.height
            layers.append(layer)
        except Exception as exc:
            exception(f'Cannot load page {fn}, exception caught!')

    if args.simulation:
        info('Starting pygame simulator hardware...')
        from led_hw_sim import HW_PyGame
        hw = HW_PyGame(loop, args.width, args.height, 5)
    else:
        info('Running with real USB hardware...')
        from led_hw_usb import HW_USB
        hw = HW_USB()

    if args.evdev:
        try:
            key_dev = evdev.InputDevice(args.evdev)
            loop.create_task(keyboard_task(key_dev))
        except Exception as exc:
            exception('Could not start evdev handler, exception raised!')
    try:
        info('Starting mainloop..')
        loop.run_until_complete(mainloop(args, layers, hw))
    except KeyboardInterrupt:
        if args.simulation:
            hw.stop()


if __name__ == '__main__':
    main()
