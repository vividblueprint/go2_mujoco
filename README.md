<div align="center">

<h1 align="center" >

<img width="25px" src="https://em-content.zobj.net/source/microsoft-teams/337/heart-with-ribbon_1f49d.png"/>
<img width="25px" src="https://em-content.zobj.net/source/microsoft-teams/337/heart-with-ribbon_1f49d.png"/>
<img width="25px" src="https://em-content.zobj.net/source/microsoft-teams/337/heart-with-ribbon_1f49d.png"/>
<b>GO2 MUJOCO</b>
<img width="25px" src="https://em-content.zobj.net/source/microsoft-teams/337/heart-with-ribbon_1f49d.png"/>
<img width="25px" src="https://em-content.zobj.net/source/microsoft-teams/337/heart-with-ribbon_1f49d.png"/>
<img width="25px" src="https://em-content.zobj.net/source/microsoft-teams/337/heart-with-ribbon_1f49d.png"/>

</h1>

[![GitHub](https://img.shields.io/badge/GitHub-vividblueprint-181717?logo=github&logoColor=white)](https://github.com/vividblueprint)
[![Issues](https://img.shields.io/github/issues/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/pulls)
[![Contributors](https://img.shields.io/github/contributors/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/graphs/contributors)
[![Stars](https://img.shields.io/github/stars/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/stargazers)
[![Forks](https://img.shields.io/github/forks/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/forks)
[![Watchers](https://img.shields.io/github/watchers/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/watchers)
[![Last Commit](https://img.shields.io/github/last-commit/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/commits)
[![Monthly Commits](https://img.shields.io/github/commit-activity/m/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/commits)
[![Languages](https://img.shields.io/github/languages/count/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco)
[![Code Size](https://img.shields.io/github/languages/code-size/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco)
[![Repo Size](https://img.shields.io/github/repo-size/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco)
[![Total Commits](https://img.shields.io/github/commit-activity/t/vividblueprint/go2_mujoco?style=flat&label=Total%20Commits)](https://github.com/vividblueprint/go2_mujoco/commits)
[![Files](https://img.shields.io/github/directory-file-count/vividblueprint/go2_mujoco?type=file&style=flat)](https://github.com/vividblueprint/go2_mujoco/tree/HEAD)
[![License](https://img.shields.io/github/license/vividblueprint/go2_mujoco?style=flat)](https://github.com/vividblueprint/go2_mujoco/blob/HEAD/LICENSE)

</div>

# go2_mujoco

Standalone Go2 MuJoCo simulator with keyboard controls, local robot assets, and
`unitree_sdk2_go2`. Uses **Python 3.11** and **CycloneDDS 11.1.0**.

### Full sim2sim/sim2real

For simple deployment check: [go2_deploy_simple](https://github.com/vividblueprint/go2_deploy_simple)

## Install

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and the
sibling `unitree_sdk2_go2` source folder. The SDK does not need a separate environment.

On Ubuntu, install the viewer libraries:

```bash
sudo apt install -y libgl1 libglfw3
```

Install the Python dependencies:

```bash
# make a directory
mkdir ~/unitree_go2
cd ~/unitree_go2/go2_mujoco

uv venv --allow-existing --python 3.11 .venv
uv pip install --python .venv/bin/python \
  --only-binary cyclonedds --reinstall-package cyclonedds \
  mujoco numpy pygame -e ../unitree_sdk2_go2
```

CycloneDDS includes its native runtime. No external DDS installation, shared
script, application `.toml`, or lockfile is needed.

## Run

```bash
cd ~/unitree_go2/go2_mujoco
.venv/bin/python simulate.py
```

In a second terminal, start the installed policy controller:

```bash
cd ~/unitree_go2/go2_deploy_simple
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
