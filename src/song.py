import wave
import pyaudio
import threading
import numpy as np

from scipy.fft import rfft

# Idk kinda looked like it made sense I have no clue to be fair.
RMS_POWER_CLIP = 10000


def normalized_fft(samples, pad):
    # pad: Minimum required length of array
    fft = np.abs(rfft(np.frombuffer(samples, np.int16)))
    if fft.shape[0] < pad:
        fft = np.concatenate((fft, np.array([0] * (pad - fft.shape[0]))))
    norm = np.linalg.norm(fft)
    return fft / (norm or 1)


def rms_power(samples):
    # Had to be rms but these numbers are more manageable.
    power = np.power(np.frombuffer(samples, np.int16), 2, dtype=np.int64)
    rms = np.sqrt(np.mean(power))
    return np.clip(rms, 0, RMS_POWER_CLIP) / RMS_POWER_CLIP


class SongMeta:
    """
    Keep info on a Song: it's name, to be shown after guessing, the clean wav file, the song's (or base) wav file, the
    vocals.
    """

    def __init__(self, name: str, solution: str, base: str, vocals: str = None):
        self.name = name
        self.solution = solution
        self.base = base
        self.vocals = vocals


class VizSong:
    """
    Abstract Song class for a Song that can be visualized.
    """

    @property
    def data(self):
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    @property
    def power(self):
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    @property
    def fft(self):
        raise NotImplementedError(f"{self.__class__} is an abstract class.")


class PlayableSong:

    def next(self):
        # Go to next song-data chunk.
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    def play(self, custom_callback=None):
        # Start playing Song. Can provide custom stream callback.
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    @property
    def playing(self):
        # Is the song playing rn?
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    def stop(self):
        # Stop playback.
        raise NotImplementedError(f"{self.__class__} is an abstract class.")

    def reset(self):
        # Stop the Song and reset it back to its first chunk.
        raise NotImplementedError(f"{self.__class__} is an abstract class.")


class WavSong(VizSong, PlayableSong):
    """
    Class that manages the song-data about a Song. Uses a mutex to be thread safe.
    Given a wav file, it pre-loads all of it in chunks of 1024 bytes and computes the fft for each chunk.
    If the fft generates less than 512 bins, bins of value 0 are added.

    Can be played and stopped.
    """

    CHUNK = 1024

    def __init__(self, path: str):
        self._pyaudio = pyaudio.PyAudio()
        wf = wave.open(path, "rb")

        self._path = path
        self._data = []
        self._pow = []
        self._fft = []
        self._index = 0
        self._lock = threading.Lock()
        self._stream = None

        self._sample_width = wf.getsampwidth()
        self._channels = wf.getnchannels()
        self._frame_rate = wf.getframerate()

        chunk = wf.readframes(WavSong.CHUNK)
        while chunk:
            self._data.append(chunk)
            self._pow.append(rms_power(chunk))
            self._fft.append(normalized_fft(chunk, WavSong.CHUNK // 2))
            chunk = wf.readframes(WavSong.CHUNK)
        # Useless sentinels for end of song.
        self._data.append("")
        self._pow.append(0)
        self._fft.append(np.array([0] * WavSong.CHUNK))

        wf.close()

    @property
    def data(self):
        # Get current chunk.
        self._lock.acquire()
        data = self._data[self._index]
        self._lock.release()
        return data

    @property
    def power(self):
        # Get current chunk's average power.
        self._lock.acquire()
        data = self._pow[self._index]
        self._lock.release()
        return data

    @property
    def fft(self):
        # Get fft for current chunk.
        self._lock.acquire()
        data = self._fft[self._index]
        self._lock.release()
        return data

    def next(self):
        # Advance to next chunk.
        self._lock.acquire()
        if self._index < len(self._data) - 1:
            self._index += 1
        self._lock.release()

    def play(self, custom_callback=None):
        # Don't play twice.
        if self._stream is not None:
            return

        # Reset index.
        self._lock.acquire()
        self._index = 0
        self._lock.release()

        # Create and start audio stream.
        def callback(in_data, frame_count, time_info, status):
            data = self.data
            self.next()
            return data, pyaudio.paContinue

        self._stream = self._pyaudio.open(
            format=self._pyaudio.get_format_from_width(self._sample_width),
            channels=self._channels,
            rate=self._frame_rate,
            output=True,
            stream_callback=custom_callback or callback
        )

        self._stream.start_stream()

    @property
    def playing(self):
        return self._stream is not None and self._stream.is_active()

    def stop(self):
        # Stop the song if it is playing.
        if self._stream is None:
            return

        self._stream.stop_stream()
        self._stream.close()
        self._stream = None

    def reset(self):
        # Stop the song and reset it to its starting point.
        self.stop()
        # Reset index.
        self._lock.acquire()
        self._index = 0
        self._lock.release()

    def __del__(self):
        self._pyaudio.terminate()


class SongPair(PlayableSong):
    """
    Class that takes two wav songs: the base and the vocals. It advances both at a time, but only plays the base on a
    stream and exposes the other as a `vocals` property.
    """

    def __init__(self, base_path: str, vocals_path: str):
        self._base_song = WavSong(base_path)
        self._vocals_song = WavSong(vocals_path)

    @property
    def vocals(self):
        return self._vocals_song

    @property
    def base(self):
        return self._base_song

    def play(self, custom_callback=None):
        # Custom callback: advance both songs instead of one.
        def callback(*args):
            data = self._base_song.data
            self._base_song.next()
            self._vocals_song.next()
            return data, pyaudio.paContinue

        self._base_song.play(custom_callback or callback)

    @property
    def playing(self):
        return self._base_song.playing

    def next(self):
        self._base_song.next()
        self._vocals_song.next()

    def reset(self):
        self.stop()
        self._base_song.reset()

    def stop(self):
        # Stop the song if it is playing.
        self._base_song.stop()
        self._vocals_song.reset()


class EmptySong(PlayableSong, VizSong):

    # Stub used for drawing visualizers without sounds.

    def __init__(self):
        self._data = bytes([0] * WavSong.CHUNK)
        self._fft = np.array([0] * (WavSong.CHUNK // 2))

    @property
    def data(self):
        return self._data

    @property
    def fft(self):
        return self._fft

    @property
    def power(self):
        return 0

    @property
    def playing(self):
        return False

    def next(self):
        pass

    def play(self, custom_callback=None):
        pass

    def stop(self):
        pass

    def reset(self):
        pass
