from abc import ABC, abstractmethod
from typing import Union

from smbus2 import smbus2

from .bitstring import BitString
from .typing import RegisterState


class Device(ABC):
    @abstractmethod
    def read_registers(self) -> RegisterState:
        pass

    @abstractmethod
    def write_registers(self, value: RegisterState, start: int = 0x00) -> None:
        pass


class I2CError(OSError):
    pass


class I2CDevice(Device):
    @property
    @abstractmethod
    def I2C_ADDRESS(self) -> int:
        """The I2C address for this device"""

    @property
    @abstractmethod
    def I2C_READ_LEN(self) -> int:
        """Default number of bytes to read via I2C"""

    @property
    @abstractmethod
    def I2C_READ_START(self) -> int:
        """Register address to begin read (default 0x00)"""
        return 0x00

    def __init__(
        self,
        i2c_bus_id: Union[int, str] = 1,
    ) -> None:
        """
        Set up I2C communication for the device.

        Parameters
        ----------
        i2c_bus_id : int, default 1
            The I2C bus ID to connect to via SMBus (RPi 4 default bus is 1)
        """
        try:
            self.bus = smbus2.SMBus(i2c_bus_id)
        except OSError as err:
            raise I2CError(
                f"Could not start I2C for bus id {i2c_bus_id}"
            ) from err

    def read_registers(self) -> RegisterState:
        """Get register state using I2C block read."""
        # TODO only read blocks needed for specific feature?
        try:
            data = self.bus.read_i2c_block_data(
                self.I2C_ADDRESS,
                self.I2C_READ_START,
                self.I2C_READ_LEN,
            )
        except Exception as err:  # FIXME what are the possible errors?
            raise I2CError("Failed to read I2C block data") from err
        return [BitString(d, fill=8) for d in data]

    def write_registers(self, values: RegisterState, start: int = 0x00) -> None:
        """
        Write register state via I2C bus

        Parameters
        ----------
        values : RegisterState
        """
        self.bus.write_i2c_block_data(self.I2C_ADDRESS, start, values)


class FakeDevice(Device):
    """
    A device which does not do any external IO, but rather keeps a local
    register state. Useful for debugging and tests.
    """

    def __init__(self):
        self.register_state: RegisterState = []

    def read_registers(self) -> RegisterState:
        return self.register_state

    def write_registers(self, value: RegisterState, start: int = 0x00) -> None:
        slice_ = slice(start, start + len(value))
        self.register_state[slice_] = value
