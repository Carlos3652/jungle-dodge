"""Root conftest: ensure real pygame is initialised before any test file.

Several test files create mock pygame stubs guarded by
``if "pygame" not in sys.modules``.  When real pygame is available we
want it loaded *first* so those guards evaluate to False and the stubs
are never injected.  This conftest runs before any test module is
collected, importing and initialising real pygame with dummy SDL drivers
so that both stub-based and real-pygame tests coexist without pollution.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
except Exception:
    pass  # pygame not installed -- stub-based tests will handle it
