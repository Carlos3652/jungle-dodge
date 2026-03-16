"""
Jungle Dodge — entry point (~30 lines).

Controls: Arrow keys / A-D to move | SPACE to start/restart | ESC to pause/quit
"""

import pygame

from constants import W, H
from persistence import PersistenceManager
from particles import ParticleSystem
from states import GameContext, GameStateManager, StartScreenState
from hud import build_background


def main():
    # pygame is already initialized by constants.py import
    display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
    screen  = pygame.Surface((W, H))
    pygame.display.set_caption("Jungle Dodge")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    ctx = GameContext(
        screen=screen,
        display=display,
        clock=clock,
        persistence=PersistenceManager(),
        particles=ParticleSystem(),
        bg=build_background(),
    )
    ctx.leaderboard = ctx.persistence.get_board("normal")

    manager = GameStateManager(ctx)
    manager.push(StartScreenState())
    manager.run()


if __name__ == "__main__":
    main()
