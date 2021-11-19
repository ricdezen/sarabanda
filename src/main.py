import json
import utils
import pygame
from telegram.ext import Updater
from game import SongGame, PokeGame

BOT_FILE = "bot.json"

SONG_FILE = "song-data/config.json"
REWIND_FILE = "song-data/rewind.wav"
VINYL_FILE = "song-data/vinyl.png"
FONT_FILE = "song-data/font.ttf"

POKEMON_FILE = "poke-data/pokemon.json"
REDUCED_POKEMON_FILE = "poke-data/pokemon-third-gen.txt"


def bot_token_and_chat_id():
    with open(BOT_FILE) as f:
        data = json.load(f)
    return data["token"], data["chat_id"]


def reduced_names():
    with open(REDUCED_POKEMON_FILE) as f:
        data = f.read()
    return [s.strip() for s in data.split("\n")]


def main():
    # Init pygame.
    pygame.init()

    # Init Telegram bot.
    token, chat_id = bot_token_and_chat_id()
    updater = Updater(token)
    updater.start_polling()

    def callback(message: str):
        updater.bot.send_message(chat_id, message)

    # Start the first game.
    game = SongGame(utils.get_songs(SONG_FILE), VINYL_FILE, REWIND_FILE, FONT_FILE, callback)
    game.play()

    # Start the second game.
    game = PokeGame(utils.get_pokemon(POKEMON_FILE, 10, reduced_names()), FONT_FILE, callback)
    game.play()

    # Release pygame.
    pygame.quit()
    updater.stop()


if __name__ == '__main__':
    main()
