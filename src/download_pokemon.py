import os

import requests

from bs4 import BeautifulSoup

CRIES_ROOT = "https://play.pokemonshowdown.com/audio/cries/"
CRIES_DIR = "poke-data/cries/"

SPRITES_ROOT = "http://play.pokemonshowdown.com/sprites/gen5ani/"
SPRITES_DIR = "poke-data/sprites/"


def is_ogg_cry(href: str):
    # Want only base pokemon in .ogg format.
    return href and href.endswith(".ogg") and len(href.split("-")) == 1


def is_gif_sprite(href: str):
    # Want only base pokemon .gif sprites.
    return href and href.endswith(".gif") and len(href.split("-")) == 1


def main():
    # Download cries.
    cries_page = requests.get(CRIES_ROOT).content
    soup = BeautifulSoup(cries_page, 'html.parser')
    for link in soup.find_all(href=is_ogg_cry):
        name = link.get("href")
        destination = CRIES_ROOT + name
        cry = requests.get(destination).content
        with open(CRIES_DIR + name, "wb+") as f:
            f.write(cry)
        print(f"Got cry for {name}.")

    # Download gen 5 gifs.
    sprites_page = requests.get(SPRITES_ROOT).content
    soup = BeautifulSoup(sprites_page, 'html.parser')
    for link in soup.find_all(href=is_gif_sprite):
        name = link.get("href")
        destination = SPRITES_ROOT + name
        gif = requests.get(destination).content
        with open(SPRITES_DIR + name, "wb+") as f:
            f.write(gif)
        print(f"Got sprite for {name}.")


if __name__ == "__main__":
    main()
