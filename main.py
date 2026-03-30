"""
Jungle Dodge — entry point (~30 lines).

Controls: Arrow keys / A-D to move | SPACE to start/restart | ESC to pause/quit
"""

import pygame

from constants import W, H
from persistence import PersistenceManager
from particles import ParticleSystem
from states import GameContext, GameStateManager, StartScreenState
from hud import build_background, HudCache
from audio import AudioManager
from themes import get_theme


def main():
    pygame.init()
    display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
    screen  = pygame.Surface((W, H))
    pygame.display.set_caption("Jungle Dodge")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    audio = AudioManager.get_instance()
    audio.load_all()

    theme = get_theme()

    ctx = GameContext(
        screen=screen,
        display=display,
        clock=clock,
        persistence=PersistenceManager(),
        particles=ParticleSystem(),
        bg=build_background(),
        hud_cache=HudCache(),
        audio=audio,
        theme=theme,
    )
    # jd-11: load persisted difficulty
    settings = ctx.persistence.load_settings()
    ctx.difficulty = settings.get("difficulty", "normal")
    ctx.leaderboard = ctx.persistence.get_board(ctx.difficulty)

    manager = GameStateManager(ctx)
    manager.push(StartScreenState())
    manager.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback, os, datetime
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
        with open(log, "a") as f:
            f.write(f"\n--- {datetime.datetime.now()} ---\n")
            traceback.print_exc(file=f)
