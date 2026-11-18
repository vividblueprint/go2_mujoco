"""Optional headless walking smoke check with the sibling simplified deployment."""
import os
from pathlib import Path
import struct
import sys

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulate import Simulator
from test_simulator import FakeDDS

DEPLOY = Path(os.environ.get('GO2_DEPLOY_SIMPLE', str(Path(__file__).resolve().parents[2] / 'go2_deploy_simple')))
sys.path.insert(0, str(DEPLOY))
from policy import PolicyController, POLICIES


class Input:
    now = 0
    def remote_bytes(self):
        remote = bytearray(40)
        for when, bit in [(1., 11), (1.3, 0), (3.5, 4), (5.7, 8)]:
            if when <= self.now < when + .15:
                struct.pack_into('<H', remote, 2, (1 << 1) | (1 << bit))
        if 7 <= self.now < 9:
            struct.pack_into('<f', remote, 20, .4)
        return remote
    def snapshot(self):
        raw = self.remote_bytes()
        return struct.unpack_from('<H', raw, 2)[0], 0., struct.unpack_from('<f', raw, 20)[0], 0., 0.


def run(name):
    dds = FakeDDS()
    keyboard = Input()
    sim = Simulator(dds, keyboard)
    controller = PolicyController(name)
    sim.bridge.publish(0)
    origin = None
    stand_height = None
    for n in range(5000):
        now = n * .002
        keyboard.now = now
        if n % 10 == 0:
            controller.update(sim.bridge.low_state, now)
        dds.commands.pending.append(controller.command)
        sim.step(now)
        if n == 2750:
            stand_height = sim.data.qpos[2]
        if n == 3500:
            origin = sim.data.qpos[:3].copy()
    displacement = sim.data.qpos[:3] - origin
    assert controller.state == 'walk'
    assert stand_height > .15
    assert np.isfinite(sim.data.qpos).all()
    assert sim.data.qpos[2] > .15, sim.data.qpos[:3]
    assert displacement[0] > .05, displacement
    print(f'{name}: standing={stand_height:.3f} m, walking={sim.data.qpos[2]:.3f} m, forward={displacement[0]:.3f} m', flush=True)


if __name__ == '__main__':
    for name in POLICIES:
        run(name)
