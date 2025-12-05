from abc import abstractmethod, ABC
from logging import info, warning, error
from pathlib import Path
from typing import List, Optional, Tuple

import PIL.Image
import numpy as np


class LEDPage(ABC):
    width: int
    height: int

    x_offset: float
    x_increment: float

    __slots__ = ['width', 'height', 'x_offset', 'x_increment']

    def __init__(self, width: int, height: int, increment: float = -1.0):
        self.x_offset = 0
        self.x_increment = increment
        self.width = width
        self.height = height

    @staticmethod
    def from_file(fn: Path, limit_brightness):
        if '.png' in fn.suffixes or '.jpg' in fn.suffixes:
            return LEDStaticImage.from_file_image(fn, limit_brightness)
        if '.ani' in fn.suffixes:
            return LEDAnimation.from_file_anim(fn, limit_brightness)
        if '.aseprite' in fn.suffixes:
            # ignore
            return None
        warning(f'Unknown extension for {fn}, ignoring!')
        return None

    @abstractmethod
    def tick(self, dt: float):
        pass

    @abstractmethod
    def get(self) -> np.ndarray:
        pass

    def rotate(self, src: np.ndarray) -> np.ndarray:
        x_offs_int = int(round(self.x_offset))

        self.x_offset += self.x_increment
        while self.x_offset < 0:
            self.x_offset += self.width
        while self.x_offset > self.width:
            self.x_offset -= self.width

        return np.roll(src, x_offs_int, axis=1)


class LEDStaticImage(LEDPage):
    img: np.ndarray

    __slots__ = ['img']

    def __init__(self, img: np.ndarray):
        super().__init__(img.shape[1], img.shape[0])  # width/height
        self.img = img

    @classmethod
    def from_file_image(cls, fn: Path, limit_brightness: int):
        img = PIL.Image.open(fn)
        if img.mode != 'RGB':
            warning(f'Image {fn} is not mode RGB, but {img.mode}.')
            img = img.convert('RGB')

        arr = np.array(img)
        vmax = np.amax(arr)
        if vmax > limit_brightness:
            info(f'{fn}: too bright {vmax}, limiting to {limit_brightness}...')
            arr = np.round(arr * (limit_brightness / vmax)).astype(np.uint8)
        return cls(arr)

    def get(self):
        return self.rotate(self.img)

    def tick(self, dt: float):
        pass


class LEDAnimation(LEDPage):
    img_arr: np.ndarray  # [n-frames,height,width,3(rgb)]
    time_arr: List[float]
    img_ix: int
    frame_dt: float

    __slots__ = ['img_arr', 'time_arr', 'img_ix', 'frame_dt']

    def __init__(self, width: int, height: int, img_arr: np.ndarray,
                 time_arr: List[float]):
        super().__init__(width, height)
        self.img_arr = img_arr
        self.time_arr = time_arr
        self.img_ix = 0
        self.frame_dt = 0.0

    @classmethod
    def from_file_anim(cls, fn: Path, limit_brightness: int):
        time_arr = []
        frames = []
        shape: Optional[Tuple] = None

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

                img = PIL.Image.open(img_fn)
                if img.mode != 'RGB':
                    warning(f'Image {fn} is not mode RGB, but {img.mode}.')
                    img = img.convert('RGB')

                ndarr = np.array(img)
                if shape is None:
                    shape = ndarr.shape
                assert np.array_equal(shape, ndarr.shape)

                frames.append(ndarr)
                time_arr.append(img_time)

        if shape is None:  # no frames!
            error('Empty animation!')
            return None

        frames = np.stack(frames, 0)

        vmax = np.amax(frames)
        if vmax > limit_brightness:
            error(f'{fn}: too bright {vmax}, limiting to {limit_brightness}...')
            frames = np.round(frames * (limit_brightness / vmax)).astype(
                np.uint8)

        info(
            f'Animation with {frames.shape[0]} frames of size {frames.shape[2]} x {frames.shape[1]}.')
        return cls(shape[1], shape[0], frames, time_arr)

    def tick(self, dt: float):
        self.frame_dt += dt
        while self.frame_dt >= self.time_arr[self.img_ix]:
            self.frame_dt -= self.time_arr[self.img_ix]
            self.img_ix += 1
            if self.img_ix >= len(self.img_arr):
                self.img_ix = 0

    def get(self):
        return self.rotate(self.img_arr[self.img_ix])
