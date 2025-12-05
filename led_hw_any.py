from abc import abstractmethod, ABC

import numpy as np


class LED_HW_Any(ABC):
    width: int
    height: int
    running: bool

    __slots__ = ['width', 'height', 'running']

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.running = True

    @abstractmethod
    def update(self, img: np.ndarray):
        pass

    @abstractmethod
    def stop(self):
        pass
