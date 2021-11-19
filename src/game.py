import ctypes
import math
from typing import Union, List, Callable

import pygame
import src.utils as utils
from animation import RotatingSprite
from poke import Pokemon
from song import SongPair, WavSong, EmptySong, SongMeta
from visualizers import RingVisualizer, BarVisualizer


class SongGame:
    """
    Take a set of wav files and present them using two visualizers.
    Allows to skip to the next song and rewind the current one.
    """

    # Would be Space.
    NEXT_KEY = 32

    # Song title font size.
    FONT_SIZE = 64

    # Vinyl record.
    VINYL_SIZE = (380, 380)
    VINYL_SPEED = 0.5
    VINYL_REWIND_SPEED = 15

    # Ring visualizer
    RING_BANDS = 128
    RING_BASE_RADIUS = 200
    RING_MAX_RADIUS = 300
    RING_MAX_LINE_LENGTH = 200

    # Bar visualizer
    BAR_BANDS = 64
    BAR_LINE_WIDTH = 7
    BAR_LINE_SPACING = 5
    BAR_MAX_LINE_LENGTH = 500

    # Bubbles
    BUBBLES = 16
    BUBBLES_REWIND_SPEED = 4

    def __init__(self, songs: List[SongMeta], vinyl_path: str, rewind_path: str, font_path: str = None,
                 callback: Callable[[str], None] = None):
        """
        :param songs: set of tuples of file paths. If Tuple of 2 strings, then consider them as song hint and
        solution. If Tuple of 3 strings, consider them as base, vocals and solution.
        :param vinyl_path: path to a vinyl record image to put at the center of the screen.
        :param rewind_path: path to a rewind sound effect to use when rewinding a song.
        :param font_path: path to a font file for song title when showing the solution. Optional.
        :param callback: Optional. Ran on each level by passing it the solution's name.
        """
        self._callback = callback
        # Init Pygame.
        # Full screen resolution on Windows fix.
        ctypes.windll.user32.SetProcessDPIAware()
        self._true_res = (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
        self._center = (self._true_res[0] // 2, self._true_res[1] // 2)

        # Load font file.
        self._font = pygame.font.Font(font_path, SongGame.FONT_SIZE)

        # Pygame utilities.
        self._clock = None
        self._screen = None
        self._scene = None

        # The two audio visualizers.
        self._ring_viz = None
        self._bar_viz = None
        self._draw_viz = None  # Drawing behaviour function.
        self._background_color = (0, 0, 0)
        self._foreground_color = (255, 255, 255)

        # Vinyl record sprite.
        self._vinyl = RotatingSprite(utils.make_frames(
            vinyl_path, SongGame.VINYL_SIZE,
            (self._center[0] - SongGame.VINYL_SIZE[0] // 2,
             self._center[1] - SongGame.VINYL_SIZE[1] // 2),
            SongGame.VINYL_SPEED
        ))
        self._rewind = WavSong(rewind_path)

        # Bubbles.
        self._bubbles = []

        # Song. May either be a SongPair or a Song based on the level.
        # If its a SongPair the two visualizers visualize the two parts.
        self._song: Union[EmptySong, SongPair, WavSong] = EmptySong()

        self._index = -1
        self._songs = []
        self._solutions = []
        self._song_names = []
        for meta in songs:
            if meta.vocals:
                self._songs.append(SongPair(meta.base, meta.vocals))
            else:
                self._songs.append(WavSong(meta.base))
            self._solutions.append(WavSong(meta.solution))
            self._song_names.append(meta.name)

        # Flag. When true, skipping means going to next song.
        # When false, skipping means showing the solution (changing the current song to the solution).
        self._showing_solution = False

    def start(self):
        # Init game song-data.
        self._clock = pygame.time.Clock()
        self._screen = pygame.display.set_mode(self._true_res)
        self._scene = pygame.Surface(self._true_res)
        self._scene.convert_alpha()

        self._ring_viz = RingVisualizer(
            self._scene,
            bands=SongGame.RING_BANDS,
            radius=SongGame.RING_BASE_RADIUS,
            max_radius=SongGame.RING_MAX_RADIUS,
            max_line_length=SongGame.RING_MAX_LINE_LENGTH
        )
        self._bar_viz = BarVisualizer(
            self._scene,
            bands=SongGame.BAR_BANDS,
            line_width=SongGame.BAR_LINE_WIDTH,
            max_line_length=SongGame.BAR_MAX_LINE_LENGTH,
            spacing=SongGame.BAR_LINE_SPACING
        )

        self._next_level()

        self._song.play()

    def play(self):
        self.start()
        # Loop through the game until its over.
        try:
            while True:
                self.loop()
        except IndexError:
            print("End of Song game.")
        self._song.stop()

    def loop(self):
        # Game loop, handle events etc.
        # Not actually a game "loop", might actually take time
        # for more complex logic spanning multiple loops (e.g. rewinding).

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYUP:
                # Skip to next level if space is pressed.
                if event.key == SongGame.NEXT_KEY:
                    if self._showing_solution:
                        self._showing_solution = False
                        self._next_level()
                    else:
                        self._showing_solution = True
                        self._change_song(self._solutions[self._index])
            if event.type == pygame.MOUSEBUTTONUP and not self._showing_solution:
                # If vinyl was clicked (190 pixels from the center), rewind song.
                x, y = pygame.mouse.get_pos()
                distance = math.sqrt((x - self._scene.get_width() / 2) ** 2 + (y - self._scene.get_height() / 2) ** 2)
                if distance < SongGame.VINYL_SIZE[0]:
                    # Play rewind sound and then restore the old song.
                    old_song = self._song
                    self._change_song(self._rewind)
                    while self._song.playing:
                        self._scene.fill(self._background_color)
                        self._rewind_bubbles()
                        self._vinyl.rewind(self._scene, SongGame.VINYL_REWIND_SPEED)
                        self._ring_viz.draw(self._song)
                        self._screen.blit(self._scene, (0, 0))
                        pygame.display.flip()
                    self._change_song(old_song)
                    break  # Avoid doing this for multiple click events.

        self._draw()

        # Maximum of 60 frames per second.
        self._clock.tick(60)

    def _change_song(self, song):
        self._song.stop()
        self._song = song

        # Change behaviour based on Song type.
        if isinstance(self._song, SongPair):
            self._draw_viz = self._draw_song_pair
        else:
            self._draw_viz = self._draw_normal_song

        self._song.play()

    def _next_level(self):
        # Stop song and play the next one.
        self._index += 1
        # Notify the callback that the song is being changed.
        self._callback(self._song_names[self._index])
        self._change_song(self._songs[self._index])

        # Pick random color for next level.
        self._background_color, self._foreground_color = utils.random_colors()
        self._ring_viz.color = self._foreground_color
        self._bar_viz.color = self._foreground_color

        # Make new bubbles and set their color.
        self._bubbles = utils.random_bubbles(SongGame.BUBBLES, self._true_res)
        for b in self._bubbles:
            b.color = self._foreground_color

        self._text_surface = self._font.render(self._song_names[self._index], True, self._foreground_color)
        self._text_rect = self._text_surface.get_rect(center=(self._true_res[0] / 2, 100))

    def _draw(self):
        self._scene.fill(self._background_color)

        # Draw bubbles
        self._draw_bubbles()

        # Draw vinyl record
        self._vinyl.draw(self._scene)

        # Only visualize Song if it is playing.
        if self._song.playing:
            self._draw_viz()

        # Only show title if showing solution.
        if self._showing_solution:
            self._scene.blit(self._text_surface, self._text_rect)

        self._screen.blit(self._scene, (0, 0))
        pygame.display.flip()

    def _draw_bubbles(self):
        for bubble in self._bubbles:
            bubble.draw(self._scene)

    def _rewind_bubbles(self):
        for bubble in self._bubbles:
            bubble.rewind(self._scene, SongGame.BUBBLES_REWIND_SPEED)

    def _draw_normal_song(self):
        self._bar_viz.draw(self._song)
        self._ring_viz.draw(self._song)

    def _draw_song_pair(self):
        self._bar_viz.draw(self._song.base)
        self._ring_viz.draw(self._song.vocals)


class PokeGame:
    """
    Take a set of wav files of pokemon cries and present them. Allows to show the silhouette or the actual image.
    """

    # Would be Space.
    NEXT_KEY = 32
    # Would be Z key.
    HINT_KEY = 122

    # Song title font size.
    FONT_SIZE = 64

    # Vinyl record.
    VINYL_SIZE = (380, 380)
    VINYL_SPEED = 0.5
    VINYL_REWIND_SPEED = 15

    # Ring visualizer
    RING_BANDS = 128
    RING_BASE_RADIUS = 200
    RING_MAX_RADIUS = 300
    RING_MAX_LINE_LENGTH = 200

    # Bar visualizer
    BAR_BANDS = 64
    BAR_LINE_WIDTH = 7
    BAR_LINE_SPACING = 5
    BAR_MAX_LINE_LENGTH = 500

    # Bubbles
    BUBBLES = 16
    BUBBLES_REWIND_SPEED = 4

    def __init__(self, pokemon: List[Pokemon], font_path: str = None, callback: Callable[[str], None] = None):
        """
        :param pokemon: collection of Pokemon, having a name, cry, sprite and silhouette.
        :param font_path: path to a font file for song title when showing the Pokemon's name. Optional.
        :param callback: Optional. Called on each new level by passing it the Pokemon's name.
        """
        self._callback = callback
        # Init Pygame.
        # Full screen resolution on Windows fix.
        ctypes.windll.user32.SetProcessDPIAware()
        self._true_res = (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
        self._center = (self._true_res[0] // 2, self._true_res[1] // 2)

        # Load font file.
        self._font = pygame.font.Font(font_path, SongGame.FONT_SIZE)

        # Pygame utilities.
        self._clock = None
        self._screen = None
        self._scene = None

        # The two audio visualizers.
        self._ring_viz = None
        self._bar_viz = None
        self._draw_viz = None  # Drawing behaviour function.
        self._background_color = (0, 0, 0)
        self._foreground_color = (255, 255, 255)

        # Pokemon data.
        self._index = -1
        self._pokemon = pokemon
        # Center the sprites in the screen.
        for p in self._pokemon:
            p.sprite.set_position(self._center)
            p.silhouette.set_position(self._center)

        # Bubbles.
        self._bubbles = []

        # Song, e.g. a Pokemon's cry.
        self._song: Union[EmptySong, SongPair, WavSong] = EmptySong()

        # Flag. When true, skipping means going to next song.
        # When false, skipping means showing the solution (changing the current song to the solution).
        self._showing_solution = False
        # Similar to above for showing the pokemon's silhouette.
        self._showing_hint = False

    def start(self):
        # Init game song-data.
        self._clock = pygame.time.Clock()
        self._screen = pygame.display.set_mode(self._true_res)
        self._scene = pygame.Surface(self._true_res)
        self._scene.convert_alpha()

        self._ring_viz = RingVisualizer(
            self._scene,
            bands=SongGame.RING_BANDS,
            radius=SongGame.RING_BASE_RADIUS,
            max_radius=SongGame.RING_MAX_RADIUS,
            max_line_length=SongGame.RING_MAX_LINE_LENGTH
        )
        self._bar_viz = BarVisualizer(
            self._scene,
            bands=SongGame.BAR_BANDS,
            line_width=SongGame.BAR_LINE_WIDTH,
            max_line_length=SongGame.BAR_MAX_LINE_LENGTH,
            spacing=SongGame.BAR_LINE_SPACING
        )

        self._next_level()

        self._song.play()

    def loop(self):
        # Game loop, handle events etc.
        # Not actually a game "loop", might actually take time
        # for more complex logic spanning multiple loops (e.g. rewinding).

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYUP:
                # Skip to next level if space is pressed.
                if event.key == SongGame.NEXT_KEY:
                    if self._showing_solution:
                        self._showing_solution = False
                        self._showing_hint = False
                        self._next_level()
                    else:
                        self._showing_solution = True
                        self._showing_hint = False
                        self._song.reset()
                        self._song.play()
                if event.key == PokeGame.HINT_KEY and not self._showing_solution:
                    # Show silhouette.
                    self._showing_hint = True
            if event.type == pygame.MOUSEBUTTONUP and not self._showing_solution:
                # If vinyl was clicked (190 pixels from the center), rewind pokemon cry.
                x, y = pygame.mouse.get_pos()
                distance = math.sqrt((x - self._scene.get_width() / 2) ** 2 + (y - self._scene.get_height() / 2) ** 2)
                if distance < SongGame.VINYL_SIZE[0]:
                    # Play the pokemon cry again.
                    self._song.reset()
                    self._song.play()
                    break

        self._draw()

        # Maximum of 60 frames per second.
        self._clock.tick(60)

    def play(self):
        self.start()
        # Loop through the game till it's over.
        try:
            while True:
                self.loop()
        except IndexError:
            print("End of Pokemon Cries game.")
        self._song.stop()

    def _change_song(self, song):
        self._song.stop()
        self._song = song
        self._song.play()

    def _next_level(self):
        # Stop song and play the next one.
        self._index += 1
        # Notify callback
        self._callback(self._pokemon[self._index].name)
        self._change_song(self._pokemon[self._index].cry)

        # Pick random color for next level (reversed w.r.t. other game)
        self._background_color, self._foreground_color = utils.random_colors()[::-1]
        self._ring_viz.color = self._foreground_color
        self._bar_viz.color = self._foreground_color

        # Make new bubbles and set their color.
        self._bubbles = utils.random_bubbles(SongGame.BUBBLES, self._true_res)
        for b in self._bubbles:
            b.color = self._foreground_color

        self._text_surface = self._font.render(self._pokemon[self._index].name, True, self._foreground_color)
        self._text_rect = self._text_surface.get_rect(center=(self._true_res[0] / 2, 100))

    def _draw(self):
        self._scene.fill(self._background_color)

        # Draw bubbles
        self._draw_bubbles()

        # Only visualize Song if it is playing.
        if self._song.playing:
            self._bar_viz.draw(self._song)
            self._ring_viz.draw(self._song)

        # Only show title if showing solution.
        if self._showing_solution:
            self._scene.blit(self._text_surface, self._text_rect)
            self._pokemon[self._index].sprite.draw(self._scene)

        if self._showing_hint:
            self._pokemon[self._index].silhouette.draw(self._scene)

        self._screen.blit(self._scene, (0, 0))
        pygame.display.flip()

    def _draw_bubbles(self):
        for bubble in self._bubbles:
            bubble.draw(self._scene)
