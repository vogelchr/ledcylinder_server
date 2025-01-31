from abc import abstractmethod, ABC
from logging import info, warning
from pathlib import Path
from typing import List

import PIL.Image
import numpy as np


class LED_Layer(ABC):
    width: int
    height: int

    x_offset: float
    x_increment: float

    def __init__(self, width: int, height: int, increment: float = -1.0):
        self.x_offset = 0
        self.x_increment = increment
        self.width = width
        self.height = height

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

    def rotate(self, src: PIL.Image.Image) -> PIL.Image.Image:
        x_offs_int = int(round(self.x_offset))

        self.x_offset += self.x_increment
        while self.x_offset < 0:
            self.x_offset += self.width
        while self.x_offset > self.width:
            self.x_offset -= self.width

        if x_offs_int == 0:  # trivial case
            return src

        width, height = src.size
        ret = PIL.Image.new('RGB', src.size)

        src_left = src.crop((0, 0, width - x_offs_int, height))
        ret.paste(src_left, (x_offs_int, 0))
        src_right = src.crop((width - x_offs_int, 0, width, height))
        ret.paste(src_right, (0, 0))

        return ret


class LED_Image(LED_Layer):
    img: PIL.Image

    def __init__(self, img: PIL.Image):
        super().__init__(*img.size)
        self.img = img

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
        return self.rotate(self.img)

    def tick(self, dt: float):
        pass


class LED_Anim(LED_Layer):
    img_arr: List[PIL.Image]
    time_arr: List[float]
    img_ix: int
    frame_dt: float

    def __init__(self, width: int, height: int, img_arr: List[PIL.Image], time_arr: List[float]):
        super().__init__(width, height)
        self.img_arr = img_arr
        self.time_arr = time_arr
        self.img_ix = 0
        self.frame_dt = 0.0

    @classmethod
    def from_file(cls, fn: Path, limit_brightness: int):
        time_arr = []
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

                img_fn_base, *arr = line.split()
                img_time = 0.1

                if len(arr) >= 1:
                    img_time = float(arr[0])

                img_fn = fn.parent / fn.stem / img_fn_base

                ndarr = np.array(PIL.Image.open(img_fn))
                if shape is None:
                    shape = ndarr.shape
                assert np.array_equal(shape, ndarr.shape)

                frames.append(ndarr)
                time_arr.append(img_time)

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
        return cls(shape[1], shape[0], img_arr, time_arr)

    def tick(self, dt: float):
        self.frame_dt += dt
        while self.frame_dt >= self.time_arr[self.img_ix]:
            self.frame_dt -= self.time_arr[self.img_ix]
            self.img_ix += 1
            if self.img_ix >= len(self.img_arr):
                self.img_ix = 0

    def get(self):
        return self.rotate(self.img_arr[self.img_ix])
