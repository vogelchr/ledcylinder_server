from pathlib import Path
import PIL.Image
from abc import abstractmethod, ABC
from logging import debug, info, warning, fatal, exception
import numpy as np


class LED_Layer(ABC):
    width: int
    height: int

    @staticmethod
    def from_file(fn: Path, limit_brightness):
        if '.png' in fn.suffixes or '.jpg' in fn.suffixes:
            return LED_Image.from_file(fn, limit_brightness)

        return RuntimeError('I do not understand what kind of layer you want to instantiate.')

    @abstractmethod
    def tick(self):
        pass

    @abstractmethod
    def get(self) -> PIL.Image.Image:
        pass


class LED_Image(LED_Layer):
    img: PIL.Image

    def __init__(self, img: PIL.Image):
        self.img = img
        self.width, self.height = self.img.size

    @classmethod
    def from_file(cls, fn: Path, limit_brightness: int):
        img = PIL.Image.open(fn)
        if img.mode != 'RGB':
            warning(f'Image {fn} is not mode RGB, but {img.mode}.')
            img = img.convert('RGB')

        arr = np.array(img)
        vmax = np.amax(arr)
        if vmax > limit_brightness:
            print(f'{fn}: too bright {vmax}, limiting to {limit_brightness}...')
            arr = np.round(arr * (limit_brightness / vmax)).astype(np.uint8)
            img = PIL.Image.fromarray(arr, 'RGB')
        return cls(img)

    def get(self):
        return self.img

    def tick(self):
        pass


