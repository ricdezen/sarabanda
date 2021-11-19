import utils
import pygame

from song import WavSong
from animation import GifSprite
from typing import Tuple


class Pokemon:
    """
    Hold info about a Pokemon. Keep its cry and animated sprite.
    """

    DESIRED_FPS = 8
    TARGET_FPS = 60
    IMAGE_SIZE = 360

    def __init__(self, name: str, sprite_path: str, cry_path: str):
        """
        :param sprite_path: The gif file with the Pokemon's sprite.
        :param cry_path: The wav file with the Pokemon's cry.
        """
        self.name = name

        # Load cry wav file.
        self.cry = WavSong(cry_path)

        # Load gif data.
        frames = utils.split_gif(sprite_path)
        sil_frames = utils.make_silhouette(frames)

        # Resize
        frames = [utils.min_resize(f, Pokemon.IMAGE_SIZE) for f in frames]
        sil_frames = [utils.min_resize(f, Pokemon.IMAGE_SIZE) for f in sil_frames]

        # Extend duration
        frames = utils.extend_frame_duration(frames, Pokemon.DESIRED_FPS, Pokemon.TARGET_FPS)
        sil_frames = utils.extend_frame_duration(sil_frames, Pokemon.DESIRED_FPS, Pokemon.TARGET_FPS)

        self.sprite = GifSprite(frames)
        self.silhouette = GifSprite(sil_frames)
