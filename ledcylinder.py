#!/usr/bin/env ./.venv/bin/python

import argparse
import asyncio
import logging
import sys
from logging import info, exception, warning, debug, error
from pathlib import Path

import evdev
import evdev.ecodes

from led_page import LEDPage
from led_sign import LEDSign
from web_api import LEDCylinderWebApi


def scan_for_keyboard():
    info('Scanning for useable keyboard...')

    for fn in evdev.list_devices():
        key_dev = evdev.InputDevice(fn)
        info(f'Trying {fn}: {key_dev}.')

        if not key_dev.name.startswith('PicoMK Pico Keyboard'):
            info(f' ..skipping, does not start with "PicoMK Pico Keyboard"')
            continue

        caps = key_dev.capabilities()
        if not evdev.ecodes.EV_KEY in caps:
            info(f' ..skipping, does not have EV_KEY capabilities!')
            continue

        if not evdev.ecodes.KEY_O in caps[evdev.ecodes.EV_KEY]:
            info(f' ..skipping, does not have an "O" key!')
            continue

        if not evdev.ecodes.KEY_I in caps[evdev.ecodes.EV_KEY]:
            info(f' ..skipping, does not have an "I" key!')
            continue

        info(' ..This keyboard seems useable!')
        return key_dev

    info('No useable keyboard found.')
    return None


async def keyboard_task(keydev: evdev.InputDevice, cmdq: asyncio.Queue[str]):
    key_pressed = dict()

    debug(f'Grabbing keyboard device {keydev}...')
    keydev.grab()

    debug('Running keyboard main loop...')
    async for evt in keydev.async_read_loop():
        evt: evdev.InputEvent

        debug(f'{evt}')

        if evt.type != evdev.ecodes.EV_KEY:
            # info(f'Not EV_KEY event: {evt}.')
            continue

        keyname = None
        if evt.code == evdev.ecodes.KEY_O:
            keyname = 'o'
        elif evt.code == evdev.ecodes.KEY_I:
            keyname = 'i'

        if keyname is None:
            debug(f'Key not I or O.')
            continue

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

        # info(f'Key processing: {keyname}.')
        cmdq.put_nowait(keyname)


async def wrap_keyboard_task(keydev: evdev.InputDevice,
                             cmdq: asyncio.Queue[str]):
    try:
        await keyboard_task(keydev, cmdq)
    except Exception as exc:
        exception('Exception caught in keyboard task!')


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
    grp.add_argument('-p', '--page-time', type=float, metavar='sec',
                     default=5.0,
                     help='Switch pages after sec seconds [def:%(default).1f]')
    grp.add_argument('-f', '--fade-time', type=float, metavar='sec',
                     default=1.0,
                     help='Switch pages after sec seconds [def:%(default).1f]')
    grp.add_argument('-l', '--limit-brightness', type=int, default=255,
                     help='Limit brightness of individual pages [def:%(default)d]')
    grp.add_argument('-r', '--randomize-pages', action='store_true',
                     help='Randomize order of pages.')

    grp = parser.add_argument_group('External Control')

    grp.add_argument('-e', '--evdev', type=str,
                     help='Support button for flash, use /dev/input/eventXX or "scan"')
    grp.add_argument('-P', '--http-port', type=int,
                     help='enable http-web api on given port')

    parser.add_argument('pages', type=Path, nargs='+')

    args = parser.parse_args()

    # confiure logging
    log_lvl = logging.INFO
    if args.verbose:
        log_lvl = logging.DEBUG
    if args.quiet:
        log_lvl = logging.WARNING

    logging.basicConfig(level=log_lvl, format='%(asctime)s %(message)s')

    if args.limit_brightness < 1 or args.limit_brightness > 255:
        error('Error: Brightness limit cannot be <1 or >255!')
        sys.exit(1)

    loop = asyncio.new_event_loop()
    cmdq = asyncio.Queue()

    if args.simulation:
        info('Starting pygame simulator hardware...')
        from led_hw_sim import HW_PyGame
        hw = HW_PyGame(loop, args.width, args.height, 5, cmdq)
    else:
        info('Running with real USB hardware...')
        from led_hw_usb import HW_USB
        hw = HW_USB()

    sign = LEDSign(hw, args.page_time, args.fade_time, args.fps, cmdq,
                   args.randomize_pages)

    if len(args.pages) == 1 and args.pages[0].is_dir():
        args.pages = sorted(args.pages[0].glob('*'))

    info('Loading pages.')
    for fn in args.pages:
        try:
            page = LEDPage.from_file(fn, args.limit_brightness)
            if page is None:
                continue
            if page.width != args.width or page.height != args.height:
                warning(
                    f'Cannot load {fn}, incorrect size ({page.width}x{page.height})!')
                continue
            sign.add_page(page)
        except Exception as exc:
            exception(f'Cannot load page {fn}, exception caught!')

    if args.http_port:
        webapi = LEDCylinderWebApi(loop, sign, args.http_port)

    key_task = None
    if args.evdev:
        key_dev = None
        try:
            if args.evdev == "scan":
                key_dev = scan_for_keyboard()
            else:
                key_dev = evdev.InputDevice(args.evdev)

            if key_dev:
                key_task = loop.create_task(wrap_keyboard_task(key_dev, cmdq))
                info(f'Using event dev {args.evdev} as control buttons...')
        except Exception as exc:
            exception('Could not start evdev handler, exception raised!')
    try:
        info('Starting mainloop..')
        loop.run_until_complete(sign.mainloop())
    except KeyboardInterrupt:
        if args.simulation:
            hw.stop()

    if key_task:
        key_task.cancel()


if __name__ == '__main__':
    main()
