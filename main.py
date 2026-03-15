"""
Jungle Dodge — entry point (task jd-06)
Run:  python main.py
"""

import pygame
import sys

from constants import W, H, FPS
from states import GameContext, GameStateManager, StartScreenState


def main():
    display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
    screen  = pygame.Surface((W, H))
    pygame.display.set_caption("Jungle Dodge")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    ctx = GameContext(screen, display, clock)
    mgr = GameStateManager(ctx)
    mgr.push(StartScreenState(mgr))

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            mgr.handle_event(event)
        mgr.update(dt)
        mgr.draw()
        ctx.present()


if __name__ == "__main__":
    main()
