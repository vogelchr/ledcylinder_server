# ledcylinder_server

## Intro

A server process written in python that plays animations on a
128x8 circular LED matrix.

## Quickstart

Place your 128x8 pixel sized images in the pages/ directory.
Then run the server like so, with the root of this repository being
the current directory.

```
./ledcylinder.py ./pages
```

### Prerequisites

Run this script, it will create a python virtualenv in `.venv` and install the prerequisites from `requirements.txt`.

```
./gen_venv.sh
```

### Simulator

Run the code as such (`-S`: simulator).

```
./ledcylinder.py -S ./pages
```

### External controller.

There's an external controller which sends keycodes for the `i` or `o` keys (us or german keyboard assumed). Key `i` flashes the whole matrix, to annoy all hackers sitting in the vicinity. Key `o` turns the matrix completely black. Use the `-e` argument to enable this feature. `-e scan` scans for one particular keyboard device.

### Allow r/w access to the magic button and the usb device.

Copy `systemd_udev/*.rules` to `/etc/udev/rules.d`. Restart (or do the udevadm dance).

### Run on startup.

Copy `systemd_udev/*.service` to `~/.config/systemd/user`, then `systemctl --user enable ledylinder.service`, then probably also `sudo loginctl enable-linger USER`, for your particular user.

