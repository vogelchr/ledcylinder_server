import numpy as np
import usb.core

from led_hw_any import LED_HW_Any


class HW_USB(LED_HW_Any):
    dev: usb.core.Device

    __slots__ = ['dev']

    def __init__(self):
        super().__init__(128, 8)
        self.dev = usb.core.find(idVendor=0xcafe, idProduct=0x4010)
        self.dev.set_configuration()
        self.dev.ctrl_transfer(0x40, 0)  # set write pointer

    # update pixel matrix from PIL Image
    def update(self, img: np.ndarray):
        self.dev.write(1, img.tobytes())

    def stop(self):
        return None
