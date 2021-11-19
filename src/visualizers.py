import math
import pygame
import numpy as np

from src.song import VizSong
from typing import Tuple


class Visualizer:
    """
    Visualize a Song by drawing on a PyGame surface.
    """

    def __init__(self, surface: pygame.Surface, bands: int = 64, line_width: int = 5, max_line_length: int = 100,
                 color: Tuple[int, int, int] = (255, 255, 255), smooth_factor: float = 0.3):
        self._surface = surface
        self._width = self._surface.get_width()
        self._height = self._surface.get_height()

        self._bands = bands
        self._line_width = line_width
        self._smooth_factor = smooth_factor
        self._max_line_length = max_line_length

        self.color = color

    def draw(self, song: VizSong):
        # Draw the song-data from a song.
        raise NotImplementedError(f"{self.__class__} is an abstract class.")


class RingVisualizer(Visualizer):
    """
    Visualize a Song by means of a rotating circle of frequency bands.
    """

    def __init__(self, surface: pygame.Surface, bands: int = 64, line_width: int = 10, max_line_length: int = 100,
                 color: Tuple[int, int, int] = (255, 255, 255), smooth_factor: float = 0.5,
                 radius: int = 100, max_radius: int = 200, speed: float = 0.5 * math.pi / 360):
        super().__init__(surface, bands, line_width, max_line_length, color, smooth_factor)

        self._max_radius = max_radius
        self._radius = radius
        self._speed = speed

        # Angle between each band.
        self._step = 2 * math.pi / self._bands

        # Angles and therefore (x,y) positions if radius were 1.
        self._angles = np.arange(0, 2 * math.pi, self._step)
        self._y_unit = np.sin(self._angles)
        self._x_unit = np.cos(self._angles)

        # Empty fft and power placeholders.
        self._fft = np.array([0] * self._bands)
        self._pow = 0

    def draw(self, song: VizSong):
        # Draw the next frame:
        # - Rotate the circle of `speed` radians.
        # - Perform exponential smoothing for fft and power.

        self._angles = (self._angles + self._speed) % 360
        self._y_unit = np.sin(self._angles)
        self._x_unit = np.cos(self._angles)

        # Exponential smoothing of fft
        new_fft = song.fft[:self._bands:] * self._max_line_length
        self._fft = new_fft * (1 - self._smooth_factor) + self._fft * self._smooth_factor

        # Exponential smoothing of radius
        self._pow = song.power * (1 - self._smooth_factor) + self._pow * self._smooth_factor
        radius = self._radius + (self._max_radius - self._radius) * self._pow

        # Compute start and end points of spectrogram lines, symmetrically to base radius.
        start_x = self._x_unit * (self._fft + radius) + self._width / 2
        end_x = self._x_unit * (radius - self._fft) + self._width / 2
        start_y = self._y_unit * (self._fft + radius) + self._height / 2
        end_y = self._y_unit * (radius - self._fft) + self._height / 2

        for i in range(self._bands):
            pygame.draw.line(
                self._surface, self.color, (start_x[i], start_y[i]), (end_x[i], end_y[i]), self._line_width
            )


class BarVisualizer(Visualizer):
    """
    Visualize a Song by means of two symmetrical bar graphs.
    """

    def __init__(self, surface: pygame.Surface, bands: int = 64, line_width: int = 5, max_line_length: int = 100,
                 color: Tuple[int, int, int] = (255, 255, 255), smooth_factor: float = 0.5, spacing: int = 1):
        super().__init__(surface, bands, line_width, max_line_length, color, smooth_factor)

        self._spacing = spacing

        # Starting positions of bars. (bands * line_width + spacing * (bands - 1))
        graph_width = bands * line_width + spacing * (bands - 1)
        self._x_left = np.arange(0, graph_width, spacing + line_width) + spacing + line_width
        self._x_right = np.arange(self._width, self._width - graph_width, -spacing - line_width) - spacing - line_width

        # Leave a bit of space from the bottom.
        self._start_y = self._height - line_width

        # Empty fft and power placeholders.
        self._fft = np.array([0] * self._bands)

    def draw(self, song: VizSong):
        # Exponential smoothing of fft
        new_fft = song.fft[:self._bands:] * self._max_line_length
        self._fft = new_fft * (1 - self._smooth_factor) + self._fft * self._smooth_factor

        for i in range(self._bands):
            pygame.draw.line(
                self._surface, self.color, (self._x_left[i], self._start_y),
                (self._x_left[i], self._start_y - self._fft[i]), self._line_width
            )
            pygame.draw.line(
                self._surface, self.color, (self._x_right[i], self._start_y),
                (self._x_right[i], self._start_y - self._fft[i]), self._line_width
            )
