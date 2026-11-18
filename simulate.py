"""Standalone MuJoCo Go2 simulator using unitree_sdk2_go2."""
import argparse
from pathlib import Path
import threading
import time

import mujoco
import mujoco.viewer
from unitree_sdk2_go2 import Go2DDS

from bridge import Go2Bridge
from keyboard import KeyboardController

ROOT = Path(__file__).resolve().parent


class Simulator:
    def __init__(self, dds, keyboard=None, dt=0.002):
        self.model = mujoco.MjModel.from_xml_path(str(ROOT / 'assets/go2/scene.xml'))
        self.model.opt.timestep = dt
        self.data = mujoco.MjData(self.model)
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.model.key('home').id)
        self.data.ctrl[:] = 0
        mujoco.mj_forward(self.model, self.data)
        self.bridge = Go2Bridge(self.model, self.data, dds, keyboard)
        self.lock = threading.Lock()

    def step(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            self.bridge.apply_command(now)
            mujoco.mj_step(self.model, self.data)
            # Publish one consistent, freshly evaluated state after integration.
            mujoco.mj_forward(self.model, self.data)
            self.bridge.publish(now)

    def run(self, duration=None, viewer=None, stop=None):
        started = time.monotonic()
        while (stop is None or not stop.is_set()) and (viewer is None or viewer.is_running()):
            tick = time.monotonic()
            if duration is not None and tick-started >= duration:
                break
            self.step(tick)
            time.sleep(max(0, self.model.opt.timestep-(time.monotonic()-tick)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true', help='Run without viewer or keyboard window')
    parser.add_argument('--duration', type=float, help='Exit after this many wall-clock seconds')
    parser.add_argument('--domain', type=int, default=1, help='Local DDS simulation domain (default: 1)')
    parser.add_argument('--dt', type=float, default=0.002, help='Physics timestep in seconds')
    args = parser.parse_args()
    if args.dt <= 0 or args.domain < 1 or (args.duration is not None and args.duration <= 0):
        parser.error('dt/duration must be positive; use a simulation domain >= 1')
    dds = Go2DDS(domain_id=args.domain, interface='lo')
    keyboard = None if args.headless else KeyboardController()
    sim = Simulator(dds, keyboard, args.dt)
    print(f'Go2 simulation: domain {args.domain}, interface lo, timestep {args.dt}s', flush=True)
    if args.headless:
        sim.run(args.duration)
        return
    stop = threading.Event()
    errors = []
    with mujoco.viewer.launch_passive(sim.model, sim.data) as viewer:
        def physics():
            try:
                sim.run(args.duration, viewer, stop)
            except BaseException as error:
                errors.append(error)
            finally:
                stop.set()
        worker = threading.Thread(target=physics, name='go2-physics')
        worker.start()
        def refresh():
            if stop.is_set():
                viewer.close()
            else:
                with sim.lock:
                    viewer.sync()
        try:
            keyboard.run(viewer, on_frame=refresh)
        finally:
            stop.set()
            worker.join()
        if errors:
            raise RuntimeError('Physics loop failed') from errors[0]


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Stopped.')
