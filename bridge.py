"""Go2-only DDS bridge. PD torques are calculated inside the physics loop."""
import mujoco
import numpy as np
from cyclonedds.internal import InvalidSample
from unitree_sdk2_go2 import LowCmd_, LowState_, SportModeState_, WirelessController_, new_message

MOTORS = [f'{leg}_{joint}' for leg in ('FR', 'FL', 'RR', 'RL') for joint in ('hip', 'thigh', 'calf')]


def quaternion_rpy(quat):
    w, x, y, z = quat
    return [float(np.arctan2(2*(w*x+y*z), 1-2*(x*x+y*y))),
            float(np.arcsin(np.clip(2*(w*y-z*x), -1, 1))),
            float(np.arctan2(2*(w*z+x*y), 1-2*(y*y+z*z)))]


class Go2Bridge:
    def __init__(self, model, data, dds, keyboard=None):
        self.dds = dds  # Keep the native DDS domain alive with the bridge.
        self.model, self.data, self.keyboard = model, data, keyboard
        if model.nu != 12 or [model.actuator(i).name for i in range(12)] != MOTORS:
            raise ValueError('This bridge requires the Go2 FR/FL/RR/RL actuator order')
        joints = model.actuator_trnid[:, 0]
        self.qpos = model.jnt_qposadr[joints]
        self.qvel = model.jnt_dofadr[joints]
        self.reader = dds.reader('rt/lowcmd', LowCmd_)
        self.low_writer = dds.writer('rt/lowstate', LowState_)
        self.sport_writer = dds.writer('rt/sportmodestate', SportModeState_)
        self.remote_writer = dds.writer('rt/wirelesscontroller', WirelessController_)
        self.low_state = new_message(LowState_)
        self.low_state.head = [0xFE, 0xEF]
        self.low_state.level_flag = 0xFF
        self.sport_state = new_message(SportModeState_)
        self.remote = new_message(WirelessController_)
        self.command = None
        self.last_command = None
        self.last_aux = -1.0
        self.dt = model.opt.timestep

    def apply_command(self, now):
        for command in self.reader.take(32):
            if not isinstance(command, InvalidSample):
                values = [[m.q, m.dq, m.kp, m.kd, m.tau] for m in command.motor_cmd[:12]]
                if np.isfinite(values).all():
                    self.command = command
                    self.last_command = now
        velocity = self.data.qvel[self.qvel]
        if self.command is None:
            torque = np.zeros(12)
        elif now - self.last_command > 0.25:
            torque = -velocity  # Damping if the controller stops publishing.
        else:
            motors = self.command.motor_cmd[:12]
            target = np.array([m.q for m in motors])
            target_velocity = np.array([m.dq for m in motors])
            kp = np.array([m.kp for m in motors])
            kd = np.array([m.kd for m in motors])
            feedforward = np.array([m.tau for m in motors])
            # Read current generalized coordinates, not last step's sensor cache.
            torque = feedforward + kp*(target-self.data.qpos[self.qpos]) + kd*(target_velocity-velocity)
            torque = np.where([m.mode == 1 for m in motors], torque, 0.0)
        self.data.ctrl[:] = np.clip(torque, self.model.actuator_ctrlrange[:, 0], self.model.actuator_ctrlrange[:, 1])

    def publish(self, now):
        low = self.low_state
        for i in range(12):
            low.motor_state[i].q = float(self.data.qpos[self.qpos[i]])
            low.motor_state[i].dq = float(self.data.qvel[self.qvel[i]])
            low.motor_state[i].tau_est = float(self.data.actuator_force[i])
        low.tick = int(self.data.time * 1000) & 0xFFFFFFFF
        low.imu_state.quaternion = self.data.sensor('imu_quat').data.tolist()
        low.imu_state.gyroscope = self.data.sensor('imu_gyro').data.tolist()
        low.imu_state.accelerometer = self.data.sensor('imu_acc').data.tolist()
        low.imu_state.rpy = quaternion_rpy(low.imu_state.quaternion)
        if self.keyboard is not None:
            low.wireless_remote = list(self.keyboard.remote_bytes())
        self.low_writer.write(low)
        if now - self.last_aux >= 0.02:
            sport = self.sport_state
            sport.position = self.data.sensor('frame_pos').data.tolist()
            sport.velocity = self.data.sensor('frame_vel').data.tolist()
            sport.body_height = sport.position[2]
            sport.yaw_speed = low.imu_state.gyroscope[2]
            sport.imu_state = low.imu_state
            sport.stamp.sec = int(self.data.time)
            sport.stamp.nanosec = int((self.data.time % 1)*1e9)
            self.sport_writer.write(sport)
            if self.keyboard is not None:
                keys, lx, ly, rx, ry = self.keyboard.snapshot()
                self.remote.keys = keys
                self.remote.lx, self.remote.ly, self.remote.rx, self.remote.ry = lx, ly, rx, ry
            self.remote_writer.write(self.remote)
            self.last_aux = now
