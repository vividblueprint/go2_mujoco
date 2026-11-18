"""Keyboard gamepad emulation, with pygame events handled on the main thread."""

import struct
import threading
import time

import pygame


class KeyboardController:
    HELP = (
        "Go2 keyboard controls",
        "Keep this window focused to control the robot.",
        "1: damping   2: sit   3: stand   4: walking policy",
        "Start with 1, 2, wait 2 seconds, 3, wait 2 seconds, 4.",
        "Hold W/S: forward/back   A/D: move left/right",
        "Hold Q/E: turn left/right",
        "Space: stop movement   1: damping   Esc: quit",
        "Release movement keys to stop. Focus loss also stops.",
    )
    # Unitree wireless_remote button bits: L1 plus Y/R1/R2/A.
    MODES = {pygame.K_1: 11, pygame.K_2: 0,
             pygame.K_3: 4, pygame.K_4: 8}

    def __init__(self):
        self._lock = threading.Lock()
        self._held = set()
        self._buttons = 0
        self._button_until = 0.0
        self._heartbeat = time.monotonic()

    def clear(self):
        with self._lock:
            self._held.clear()
            self._buttons = 0

    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.clear()
        elif event.type == pygame.KEYUP:
            with self._lock:
                self._held.discard(event.key)
        elif event.type == pygame.KEYDOWN:
            with self._lock:
                if event.key in self._held:
                    return
                self._held.add(event.key)
                if event.key == pygame.K_SPACE or event.key in self.MODES:
                    self._held.intersection_update(self.MODES)
                if event.key in self.MODES:
                    self._buttons = (1 << 1) | (1 << self.MODES[event.key])
                    self._button_until = time.monotonic() + 0.15

    def heartbeat(self):
        with self._lock:
            self._heartbeat = time.monotonic()

    def snapshot(self):
        """Return buttons and normalized stick axes; stale UI input is neutral."""
        with self._lock:
            now = time.monotonic()
            if now - self._heartbeat > 0.3:
                return 0, 0.0, 0.0, 0.0, 0.0
            buttons = self._buttons if now < self._button_until else 0
            held = self._held
            # The deployment controller negates lx and rx.
            lx = 0.4 * ((pygame.K_d in held) - (pygame.K_a in held))
            ly = 0.4 * ((pygame.K_w in held) - (pygame.K_s in held))
            rx = 0.5 * ((pygame.K_e in held) - (pygame.K_q in held))
            return buttons, lx, ly, rx, 0.0

    def remote_bytes(self):
        buttons, lx, ly, rx, ry = self.snapshot()
        data = bytearray(40)
        struct.pack_into("<H", data, 2, buttons)
        struct.pack_into("<fff", data, 4, lx, rx, ry)
        struct.pack_into("<f", data, 20, ly)
        return data

    def run(self, viewer, on_frame=None):
        pygame.init()
        try:
            screen = pygame.display.set_mode((660, 330))
            pygame.display.set_caption("Go2 keyboard controls")
            font = pygame.font.Font(None, 25)
            clock = pygame.time.Clock()
            print("\n".join(self.HELP))
            while viewer.is_running():
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (
                        event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    ):
                        return
                    self.handle_event(event)
                self.heartbeat()
                if on_frame is not None:
                    on_frame()
                screen.fill((25, 30, 40))
                for i, line in enumerate(self.HELP):
                    screen.blit(font.render(line, True, (235, 240, 245)), (18, 20 + i * 36))
                pygame.display.flip()
                clock.tick(60)
        finally:
            self.clear()
            viewer.close()
            pygame.quit()
