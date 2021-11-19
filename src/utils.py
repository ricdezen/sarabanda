import json
import random
import numpy as np
import pygame.image

from poke import Pokemon
from PIL import Image
from pathlib import Path
from song import SongMeta
from animation import Bubble
from typing import List, Tuple


def get_songs(file: str) -> List[SongMeta]:
    """
    :param file: json file containing the song's song-data. Must have three main sections: "no-vocals", "distorted",
    "reversed". For each it must have a list of metadata, one item per song. Each metadata must contain name, clean song
    and base song, and optionally vocals, if the base and the vocals have to be shown separately. Paths of the files
    have to be relative to the json file's parent.
    :return: A list of SongMeta.
    """
    # Load info.
    with open(file) as fp:
        data = json.load(fp)

    songs = []
    file = Path(file)
    # Make sure the order is no-vocals -> distorted -> reversed.
    for s in data["no-vocals"] + data["distorted"] + data["reversed"]:
        name = s["name"]
        solution = str(Path(file.parent, s["solution"]))
        base = str(Path(file.parent, s["base"]))
        vocals = str(Path(file.parent, s["vocals"])) if "vocals" in s else None
        songs.append(SongMeta(name, solution, base, vocals))
    return songs


def get_pokemon(file: str, n: int, restrict: List[str] = None) -> List[Pokemon]:
    """
    :param file: Json file. Needs to contain at least a "pokemon" item, which is a list of dictionaries each having the
    pokemon name, cry wav file location and sprite gif location. File paths have to be relative w.r.t. the given file's
    parent.
    :param n: How many random pokemon to load.
    :param restrict: If not empty only choose pokemon from the intersection of the two lists.
    :return: The Pokemon indexed by the given file.
    """
    with open(file) as fp:
        data = json.load(fp)

    pokemon_info = {}
    file = Path(file)
    for p in data["pokemon"]:
        name = p["name"]
        cry = str(Path(file.parent, p["cry"]))
        sprite = str(Path(file.parent, p["sprite"]))
        pokemon_info[name] = (sprite, cry)

    pokemon = []
    admissible = list(set(pokemon_info.keys()).intersection(set(restrict)) if restrict else set(pokemon_info.keys()))
    for _ in range(n):
        name = random.choice(admissible)
        pokemon.append(Pokemon(name, pokemon_info[name][0], pokemon_info[name][1]))
    return pokemon


def split_gif(gif_path) -> List[pygame.Surface]:
    """
    Split a gif into its frames.

    :param gif_path: Gif image file.
    :return: A list of pygame surfaces, with color key on (0,0,0).
    """
    frames = []
    gif = Image.open(gif_path)
    gif.seek(0)
    palette = gif.getpalette()
    for i in range(gif.n_frames):
        gif.seek(i)

        # I refuse to investigate further as to
        # why this terrible step is needed.
        # Oh ok its because gifs have an n-color palette.
        gif.putpalette(palette)
        frame = Image.new("RGB", gif.size)
        frame.paste(gif)

        matrix = np.transpose(np.array(frame), (1, 0, 2))
        color = frame.getpixel((0, 0))
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                # Remove background
                if tuple(matrix[i, j]) == color:
                    matrix[i, j] = (0, 0, 0)
                # Avoid originally black pixels to be masked away later.
                elif tuple(matrix[i, j]) == (0, 0, 0):
                    matrix[i, j] = (1, 1, 1)

        surface = pygame.surfarray.make_surface(matrix)
        surface.set_colorkey((0, 0, 0))
        frames.append(surface)
    return frames


def make_silhouette(frames: List[pygame.Surface]) -> List[pygame.Surface]:
    """
    Make silhouettes from frames.

    :param frames: Frames of the sprite.
    :return: A list of surfaces where every non black pixel has been set to (1,1,1).
    """
    sil_frames = []
    for f in frames:
        matrix = pygame.surfarray.pixels3d(f).copy()
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                # Remove background
                if tuple(matrix[i, j]) != (0, 0, 0):
                    matrix[i, j] = (1, 1, 1)
        surface = pygame.surfarray.make_surface(matrix)
        surface.set_colorkey((0, 0, 0))
        sil_frames.append(surface)
    return sil_frames


def extend_frame_duration(frames: List[pygame.Surface], desired_fps: int, target_fps: int) -> List[pygame.Surface]:
    """
    :param frames: List of surfaces.
    :param desired_fps: The desired animation frames per second.
    :param target_fps: The target actual frames per second.
    :return: A List containing multiple copies of the original frames to better match the desired animation speed.
    """
    copies = target_fps // desired_fps
    new_frames = []
    for f in frames:
        for _ in range(copies):
            new_frames.append(f)
    return new_frames


def min_resize(surface: pygame.Surface, target_size: int) -> pygame.Surface:
    # Resize an image, keeping the aspect ratio. Its maximum side will be as big as the desired one.
    width, height = surface.get_width(), surface.get_height()
    if width < height:
        # Less wide than high
        new_h = target_size
        # width : height = new_w : new_h
        new_w = int(new_h * width / height)
        return pygame.transform.scale(surface, (new_w, new_h))
    else:
        # Less high than wide
        new_w = target_size
        # width : height = new_w : new_h
        new_h = int(new_w * height / width)
        return pygame.transform.scale(surface, (new_w, new_h))


def make_frames(source: str, size: tuple, pivot: tuple, speed: float):
    # Make a list of (image, rect) from a starting one, rotating 360 degrees with a certain speed.
    image = pygame.transform.scale(pygame.image.load(source), size)
    frames = [(image, image.get_rect(topleft=pivot))]
    for i in np.arange(0, -360, -speed):
        rotated = pygame.transform.rotate(frames[0][0], i)
        new_rect = rotated.get_rect(center=image.get_rect(topleft=pivot).center)
        frames.append((rotated, new_rect))
    return frames


def random_colors():
    # Get a random dark background color and its complementary for the foreground.
    background = (random.choice(range(0, 100)), random.choice(range(0, 100)), random.choice(range(0, 100)))
    foreground = (255 - background[0], 255 - background[1], 255 - background[2])
    return background, foreground


def random_bubbles(n: int, scene_res: Tuple[int, int]):
    # Generate n random white bubbles.
    bubbles = [Bubble(
        (255, 255, 255),
        (random.randint(0, scene_res[0]), random.randint(0, scene_res[1])),  # Random position.
        (random.random() * 6 - 3, random.random() * 6 - 3),  # Random speed from -1 to 1.
        random.random() * 2 + 1,  # Random growth from 1 to 3
        random.randint(100, 200),  # Lifespan of 100 to 600 frames
        random.randint(600, 1200),  # Downtime of 600 to 1200 frames
        random.randint(1, 100)  # No more than 100 alpha
    ) for _ in range(n)]
    for b in bubbles:
        b.randomize()
    return bubbles
