from pathlib import Path
import PIL.Image
from abc import abstractmethod, ABC
from logging import debug, info, warning, fatal, exception
import numpy as np
from typing import List


class LED_Layer(ABC):
    width: int
    height: int

    @staticmethod
    def from_file(fn: Path, limit_brightness):
        if '.png' in fn.suffixes or '.jpg' in fn.suffixes:
            return LED_Image.from_file(fn, limit_brightness)
        if '.ani' in fn.suffixes:
            return LED_Anim.from_file(fn, limit_brightness)
        warning(f'Unknown extension for {fn}, ignoring!')
        return None

    @abstractmethod
    def tick(self, dt: float):
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

    def tick(self, dt: float):
        pass


class LED_Anim(LED_Layer):
    img_arr: List[PIL.Image]
    img_ix: int
    frame_dt: float

    def __init__(self, width: int, height: int, img_arr: List[PIL.Image]):
        self.width = width
        self.height = height
        self.img_arr = img_arr
        self.img_ix = 0
        self.frame_dt = 0.0

    @classmethod
    def from_file(cls, fn: Path, limit_brightness: int):
        frames = []
        shape = None

        info(f'Loading animation from {fn}...')
        with fn.open() as f:
            for line in f:
                if (ix := line.find('#')) != -1:
                    line = line[:ix]
                line = line.strip()
                if not line:
                    continue

                img_fn = fn.parent / fn.stem / line

                ndarr = np.array(PIL.Image.open(img_fn))
                if shape is None:
                    shape = ndarr.shape
                assert np.array_equal(shape, ndarr.shape)
                frames.append(ndarr)

        frames = np.stack(frames, 0)

        vmax = np.amax(frames)
        if vmax > limit_brightness:
            print(f'{fn}: too bright {vmax}, limiting to {limit_brightness}...')
            frames = np.round(
                frames * (limit_brightness / vmax)).astype(np.uint8)

        img_arr = []
        for k in range(frames.shape[0]):
            img_arr.append(PIL.Image.fromarray(frames[k]))
        info(
            f'Animation with {len(img_arr)} frames of size {shape[1]} x {shape[0]}')
        return cls(shape[1], shape[0], img_arr)

    def tick(self, dt: float):
        self.frame_dt += dt
        while self.frame_dt >= 0.1:
            self.frame_dt -= 0.1
            self.img_ix += 1
            if self.img_ix >= len(self.img_arr):
                self.img_ix = 0

    def get(self):
        return self.img_arr[self.img_ix]
