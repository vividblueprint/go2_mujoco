import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keyboard import KeyboardController


class KeyboardTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch("keyboard.time.monotonic", return_value=10.0)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.keyboard = KeyboardController()

    def event(self, kind, key):
        self.keyboard.handle_event(pygame.event.Event(kind, key=key))

    def test_buttons_match_deployment_startup_sequence(self):
        for key, bit in [(pygame.K_1, 11), (pygame.K_2, 0),
                         (pygame.K_3, 4), (pygame.K_4, 8)]:
            self.event(pygame.KEYDOWN, key)
            remote = self.keyboard.remote_bytes()
            self.assertEqual(struct.unpack_from("<H", remote, 2)[0], (1 << 1) | (1 << bit))
            self.event(pygame.KEYUP, key)
            self.now.return_value += 0.2
            self.keyboard.heartbeat()
            self.assertEqual(self.keyboard.snapshot()[0], 0)

    def test_axes_and_release(self):
        for key in (pygame.K_w, pygame.K_a, pygame.K_q):
            self.event(pygame.KEYDOWN, key)
        remote = self.keyboard.remote_bytes()
        self.assertAlmostEqual(struct.unpack_from("<f", remote, 20)[0], 0.4)
        self.assertAlmostEqual(struct.unpack_from("<f", remote, 4)[0], -0.4)
        self.assertAlmostEqual(struct.unpack_from("<f", remote, 8)[0], -0.5)
        for key in (pygame.K_w, pygame.K_a, pygame.K_q):
            self.event(pygame.KEYUP, key)
        self.assertEqual(self.keyboard.snapshot(), (0, 0, 0, 0, 0))

    def test_stop_focus_loss_and_stale_input(self):
        for stop in ("space", "focus", "stale", "mode"):
            with self.subTest(stop=stop):
                self.keyboard = KeyboardController()
                self.event(pygame.KEYDOWN, pygame.K_w)
                if stop == "space":
                    self.event(pygame.KEYDOWN, pygame.K_SPACE)
                elif stop == "focus":
                    self.keyboard.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
                elif stop == "mode":
                    self.event(pygame.KEYDOWN, pygame.K_1)
                else:
                    self.now.return_value += 0.4
                self.assertEqual(self.keyboard.snapshot()[1:], (0, 0, 0, 0))

    def test_key_repeat_does_not_retrigger_mode(self):
        self.event(pygame.KEYDOWN, pygame.K_2)
        self.now.return_value += 0.2
        self.keyboard.heartbeat()
        self.event(pygame.KEYDOWN, pygame.K_2)
        self.assertEqual(self.keyboard.snapshot()[0], 0)


if __name__ == "__main__":
    unittest.main()
