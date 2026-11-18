# go2_mujoco

Standalone Go2 MuJoCo simulator with keyboard controls, local robot assets, and
`unitree_sdk2_go2`. Uses **Python 3.11** and **CycloneDDS 11.1.0**.

## Install

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and the
sibling `unitree_sdk2_go2` source folder. The SDK does not need a separate environment.

On Ubuntu, install the viewer libraries:

```bash
sudo apt install -y libgl1 libglfw3
```

Install the Python dependencies:

```bash
cd /home/shamim/playground/unitree_go2/shamim/go2_mujoco
uv venv --allow-existing --python 3.11 .venv
uv pip install --python .venv/bin/python \
  --only-binary cyclonedds --reinstall-package cyclonedds \
  mujoco numpy pygame -e ../unitree_sdk2_go2
```

CycloneDDS includes its native runtime. No external DDS installation, shared
script, application `.toml`, or lockfile is needed.

## Run

```bash
cd /home/shamim/playground/unitree_go2/shamim/go2_mujoco
.venv/bin/python simulate.py
```

In a second terminal, start the installed policy controller:

```bash
cd /home/shamim/playground/unitree_go2/shamim/go2_deploy_simple
.venv/bin/python deploy.py --policy ts
```

The simulator and deployment use local DDS domain **1** on **lo**. Stop other
simulators and motor controllers on that domain first. The simulator needs an
external controller to stand or walk; it does not provide Sport RPC commands.

## Keyboard

Click the **Go2 keyboard controls** window:

1. **1**: damping.
2. **2**: sit; wait **2 seconds**.
3. **3**: stand; wait **2 seconds**.
4. **4**: enable walking.

Hold **W/S** for forward/backward, **A/D** for sideways, and **Q/E** for turning.
**Space** stops movement, **1** returns to damping, and **Escape** closes the
simulator. Releasing movement keys or changing focus clears movement input.

## Headless mode

```bash
.venv/bin/python simulate.py --headless
# Or exit after three seconds on a separate domain:
.venv/bin/python simulate.py --headless --domain 79 --duration 3
```

Headless mode has no keyboard window. Defaults are a 2 ms physics timestep and
local domain 1. `--dt` and `--domain` change these settings; controllers must use
the same domain.

## Test

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The bridge calculates torques from current joint state, enforces motor torque
limits, and switches to damping after 0.25 seconds without commands. Robot assets
retain the Unitree license in `LICENSE`. No original SDK or simulator is imported.
