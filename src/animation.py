import itertools
import random

import numpy as np
import pygame

from typing import List, Tuple


class Sprite:

    def draw(self, surface: pygame.Surface):
        # Draw next frame (looping back to the first if we ran out).
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    def rewind(self, surface: pygame.Surface, frames: int = -1):
        # Draw a previous frame and set back the index, effectively rewind the animation.
        raise NotImplementedError(f"{self.__class__} is an abstract class.")


class RotatingSprite(Sprite):
    """
    Basic rotating sprite from a list of Surfaces + rect (since rotated images can have different sizes).
    """

    def __init__(self, frames: List[pygame.Surface]):
        self._frames = frames
        self._index = 0

    def draw(self, surface: pygame.Surface):
        # Draw next frame (looping back to the first if we ran out).
        frame, rect = self._frames[self._index]
        surface.blit(frame, rect)
        self._index = (self._index + 1) % len(self._frames)

    def rewind(self, surface: pygame.Surface, frames: int = 1):
        # Draw a previous frame and set back the index, effectively rewind the animation.
        self._index = (self._index - frames) % len(self._frames)
        frame, rect = self._frames[self._index]
        surface.blit(frame, rect)


class GifSprite(Sprite):
    """
    Basic static sprite from a list of Surfaces. Uses per-pixel alpha since it has been conceived for Pokemon sprite
    gifs. Assumes all frames to be of the same size. Needs to be provided a position to be drawn properly. Can be
    updated via `set_position`.
    """

    def __init__(self, frames: List[pygame.Surface], position: Tuple[int, int] = (0, 0)):
        self._frames = frames
        self._index = 0

        shift_x, shift_y = self._frames[0].get_width() // 2, self._frames[0].get_height() // 2
        self._position = (position[0] - shift_x, position[1] - shift_y)

    def draw(self, surface: pygame.Surface):
        # Draw next frame (looping back to the first if we ran out).
        frame = self._frames[self._index]
        surface.blit(frame, (self._position[0], self._position[1]))
        self._index = (self._index + 1) % len(self._frames)

    def rewind(self, surface: pygame.Surface, frames: int = 1):
        # Draw a previous frame and set back the index, effectively rewind the animation.
        self._index = (self._index - frames) % len(self._frames)
        frame = self._frames[self._index]
        surface.blit(frame, (self._position[0], self._position[1]))

    def set_position(self, position: Tuple[int, int]):
        # Update position (of gif center).
        shift_x, shift_y = self._frames[0].get_width() // 2, self._frames[0].get_height() // 2
        self._position = (position[0] - shift_x, position[1] - shift_y)


class Bubble(Sprite):
    """
    A Bubble that grows becoming more and more transparent as it reaches the end of its lifespan.
    Has a downtime before appearing again and starting over.
    """

    def __init__(self, color: Tuple[int, int, int], position: Tuple[int, int], speed: Tuple[float, float],
                 growth: float, lifespan: int, downtime: int, max_alpha: int):
        """
        :param color: Color of the bubble. Any except black which is used for color keying.
        :param position: Position of the center of the bubble in the surface given to draw.
        :param speed: X and Y speed at each frame.
        :param growth: The radius growth rate in pixels per frame.
        :param lifespan: The lifespan in frames. Bubble grows and fades until it reaches 0 alpha.
        :param downtime: How many frames to wait before starting over.
        :param max_alpha: The alpha at the start of each animation cycle.
        """
        # Color can be changed from outside.
        self.color = color

        # The rest has to remain constant.
        self._scene_pos = position
        self._growth = growth
        self._lifespan = lifespan
        self._downtime = downtime

        self._index = 0
        self._radius = [int(r) for r in np.arange(0, growth * lifespan, growth)] + [0] * downtime
        self._opacity = [int(o) for o in np.arange(max_alpha, 0, - max_alpha / lifespan)] + [0] * downtime

        # Temporary surface as big as we could need.
        self._width, self._height = growth * lifespan * 2, growth * lifespan * 2
        self._center = (self._width // 2, self._height // 2)
        self._shift_x = [int(x) for x in np.arange(0, lifespan * speed[0], speed[0])] + [0] * downtime
        self._shift_y = [int(y) for y in np.arange(0, lifespan * speed[1], speed[1])] + [0] * downtime

        self._surf = pygame.surface.Surface((self._width, self._height))
        self._surf.set_colorkey((0, 0, 0))

    def draw(self, surface: pygame.Surface):
        # Draw next frame (looping back to the first if we ran out).
        self._draw(surface)
        self._index = (self._index + 1) % len(self._radius)

    def rewind(self, surface: pygame.Surface, frames: int = 1):
        # Draw a previous frame and set back the index, effectively rewind the animation.
        self._index = (self._index - frames) % len(self._radius)
        self._draw(surface)

    def randomize(self):
        # Choose random frame.
        self._index = random.randint(0, len(self._radius) - 1)

    def _draw(self, surface: pygame.Surface):
        index = self._index
        radius = self._radius[index]
        if not radius:
            return  # No need to blit (either during downtime or too small).

        surf = self._surf
        surf.fill((0, 0, 0))

        # Draw circle with correct size.
        pygame.draw.circle(surf, self.color, self._center, radius)
        surf.set_alpha(self._opacity[index])

        pos = (self._scene_pos[0] + self._shift_x[index], self._scene_pos[1] + self._shift_y[index])
        surface.blit(surf, pos)
