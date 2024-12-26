import usb.core
import PIL.Image


class HW_USB:
    def __init__(self):
        self.dev = usb.core.find(idVendor=0xcafe, idProduct=0x4010)
        self.dev.set_configuration()
        self.dev.ctrl_transfer(0x40, 0)  # set write pointer
        self.width = 128
        self.height = 8
        self.running = True

    # update pixel matrix from PIL Image
    def update(self, img: PIL.Image.Image):
        self.dev.write(1, img.tobytes())
