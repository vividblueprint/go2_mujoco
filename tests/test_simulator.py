import unittest

import mujoco
import numpy as np
from unitree_sdk2_go2 import low_command

from simulate import Simulator


class Reader:
    def __init__(self):
        self.pending = []
    def take(self, count):
        result, self.pending = self.pending[:count], self.pending[count:]
        return result


class Writer:
    def __init__(self):
        self.message = None
    def write(self, message):
        self.message = message


class FakeDDS:
    def __init__(self):
        self.commands = Reader()
        self.outputs = {}
    def reader(self, *args, **kwargs):
        return self.commands
    def writer(self, topic, *args, **kwargs):
        self.outputs[topic] = Writer()
        return self.outputs[topic]


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.dds = FakeDDS()
        self.sim = Simulator(self.dds)

    def test_simulator_keeps_its_dds_connection_alive(self):
        import gc
        import weakref
        dds = FakeDDS()
        reference = weakref.ref(dds)
        sim = Simulator(dds)
        del dds
        gc.collect()
        self.assertIsNotNone(reference())

    def test_pd_uses_current_joint_state_not_cached_sensors(self):
        cmd = low_command()
        index = self.sim.bridge.qpos[0]
        cmd.motor_cmd[0].q = float(self.sim.data.qpos[index] + .01)
        cmd.motor_cmd[0].kp = 10
        self.sim.data.sensordata[0] = 100
        self.dds.commands.pending.append(cmd)
        self.sim.bridge.apply_command(0)
        self.assertAlmostEqual(self.sim.data.ctrl[0], .1, places=6)

    def test_torque_limits_and_stale_command_damping(self):
        cmd = low_command()
        cmd.motor_cmd[0].tau = 1000
        self.dds.commands.pending.append(cmd)
        self.sim.bridge.apply_command(0)
        self.assertEqual(self.sim.data.ctrl[0], self.sim.model.actuator_ctrlrange[0, 1])
        self.sim.data.qvel[self.sim.bridge.qvel] = 1
        self.sim.bridge.apply_command(.3)
        np.testing.assert_allclose(self.sim.data.ctrl, -np.ones(12))

    def test_motor_order_and_imu_state(self):
        for i, adr in enumerate(self.sim.bridge.qpos):
            self.sim.data.qpos[adr] = .01*i
        mujoco.mj_forward(self.sim.model, self.sim.data)
        self.sim.bridge.publish(0)
        state = self.dds.outputs['rt/lowstate'].message
        np.testing.assert_allclose([m.q for m in state.motor_state[:12]], .01*np.arange(12))
        self.assertEqual(len(state.motor_state), 20)
        self.assertEqual(len(state.wireless_remote), 40)
        np.testing.assert_allclose(state.imu_state.quaternion, [1, 0, 0, 0])
        np.testing.assert_allclose(state.imu_state.rpy, [0, 0, 0])
        self.assertIn('rt/sportmodestate', self.dds.outputs)
        self.assertIn('rt/wirelesscontroller', self.dds.outputs)

    def test_invalid_command_is_ignored(self):
        cmd = low_command()
        cmd.motor_cmd[0].tau = float('nan')
        self.dds.commands.pending.append(cmd)
        self.sim.bridge.apply_command(0)
        self.assertIsNone(self.sim.bridge.command)
        np.testing.assert_array_equal(self.sim.data.ctrl, np.zeros(12))


if __name__ == '__main__':
    unittest.main()
