from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, Type, TypeVar, Union

from .devices import I2CDevice
from .parsers import RegisterParser
from .typing import RegisterState

BlockType = TypeVar("BlockType")


class RegisterBlock(Generic[BlockType], ABC):
    """
    Abstract base class for collections of registers that represent distinct
    features of an I2C device. A RegisterBlock translates between high-level
    data structures and the low-level representation of that data as expressed
    by RegisterParsers. For example, for the DS series RTCs, there are sub-
    classes of RegisterBlock for the clock, the alarms, and their configuration
    states. The Clock subclass encapsulates RegisterParsers for the BCD-ish
    encoding of the Hour, Minute, Second, etc. stored in the device registers.

    RegisterBlock is a Generic type. When subclassing, add the appropriate type
    for the value represented by the subclass to its signature:

      class TimekeepingRegisterBlock(RegisterBlock[datetime]): ...

    A RegisterBlock subclass should define one or more attributes that are
    RegisterParsers. Subclasses must also define two methods:

     1) `_value` to read the data from its attributes and produce a value of
        the designated type
     2) `_prepare_update` to set its attributes to a given value

    For example, suppose some device stored a positive decimal number like
    12.34 with the integer part in register 0x00 and the fractional part in
    register 0x01, each represented as 2 digit standard BCD. You want to read
    or write this value as a 2-tuple of ints. A RegisterBlock for accessing
    this number could be:

        class DecimalRegisterBlock(RegisterBlock[Tuple[int, int]]):
            integer_part = BCDRegisterParser(0x00)
            fractional_part = BCDRegisterParser(0x01)

            def _value(self) -> Tuple[int, int]:
                return self.integer_part, self.fractional_part

            def _prepare_update(self, value: Tuple[int, int]) -> None:
                self.integer_part, self.fractional_part = value
    """

    @property
    def register_state(self) -> "RegisterState":
        """
        Accesses register state from the most recent read of the parent device.
        """
        return self._register_state

    @register_state.setter
    def register_state(self, state: "RegisterState") -> None:
        """
        Setting register_state also keeps a copy to use as pending_state.
        """
        self._register_state = state
        self.pending_state = self._register_state.copy()

    def __init__(self) -> None:
        """
        Initialize a new RegisterBlock. RegisterBlock is a data descriptor, so
        it must be used as an attribute on a subclass of I2CDevice in order to
        have access to the device register state.
        """
        # The very first access to the descriptor will populate actual state.
        self.register_state: RegisterState = []

    def __get__(
        self, instance: "I2CDevice", owner: Type["I2CDevice"]
    ) -> BlockType:
        """
        RegisterBlock is a data descriptor with access to the state of the
        I2CDevice instance that it belongs to, so we can use that register
        state for all parsers associated with this RegisterBlock (see
        RegisterParser.__get__).

        It is important for all RegisterParser instances to have a shared
        register state (i.e. the state stored in this class) in order to avoid
        mistakes if the state changes during a read. For example, if an RTC's
        Second register is read at 0 minutes 59 seconds, and then the clock
        ticks before we read the Minute register, the time would come out as
        1 minute 59 seconds. Maxim DS RTCs (and probably others) use of 2 sets
        of registers to prevent this issue from affecting I2C block reads, so
        we just need to make sure we only make one call to `read_registers()`
        for all the RegisterParsers within a RegisterBlock.
        """
        if not instance:
            raise AttributeError(
                "RegisterBlock must be accessed from an I2CDevice instance."
            )
        self.register_state = instance.read_registers()
        return self._value()

    def __set__(self, instance: "I2CDevice", value: BlockType) -> None:
        """
        Setting the value of the RegisterBlock updates its state via the
        RegisterParser descriptors that belong to the block.
        """
        # Make sure we have the latest state loaded before modifying it
        self.register_state = instance.read_registers()
        self._prepare_update(value)
        # A minor optimization to only write a contiguous block from the first
        # changed register to the last changed register, leaving the rest
        # unmodified. This helps improve the speed of small updates.
        addresses_changed = [
            i
            for i, b in enumerate(self.pending_state)
            if b != self._register_state[i]
        ]
        first_changed = min(addresses_changed)
        last_changed = max(addresses_changed)
        to_write = self.pending_state[first_changed : last_changed + 1]
        instance.write_registers(to_write, first_changed)

    @abstractmethod
    def _prepare_update(self, value: BlockType) -> None:
        """
        Subclasses should define behavior for setting the values of their
        RegisterParser attributes to reflect the requested `value` for the
        RegisterBlock. Parsers' `__set__` methods call `update_register_state`
        on this instance so they can all keep their pending state in sync.
        """

    @abstractmethod
    def _value(self) -> BlockType:
        """
        Value should return an appropriate object to represent the state of
        this register block e.g. a datetime for the clock/alarms or a float for
        the temperature
        """

    def update_register_state(
        self, address: Union[int, slice], value: "RegisterState"
    ) -> None:
        """
        RegisterParsers should call this method to stage their changes to the
        register state. This allows parsers to be aware of each other's pending
        changes so e.g. two distinct parsers can flip two different bits in the
        same register. Once all parsers have staged their changes (implement
        via _prepare_update), the __set__ method will write all the changes to
        the parent I2CDevice instance.

        Parameters
        ----------
        address : Union[int, slice]
            The register address(es) to set

        value : RegisterState
            The bytes to insert at address
        """
        if isinstance(address, int):
            address = slice(address, address + 1)
        if len(value) != len(self.pending_state[address]):
            raise ValueError("Value must have as many bytes as slice")
        self.pending_state[address] = value


class DatetimeRegisterBlock(RegisterBlock[datetime]):
    """
    Base class whose subclasses keep track of the register addresses where
    various components of the date/time/alarms are stored for RTC ICs such
    as the Maxim DS series.
    """

    hour: RegisterParser[int]
    minute: RegisterParser[int]
    day_of_month: RegisterParser[int]

    # Define defaults for attributes that may be left unset, e.g. the DS3231
    # and DS1337 have no seconds for Alarm 2, and no year or month for either
    # Alarm.
    @property
    def second(self) -> Union[RegisterParser[int], int]:
        return 0

    @second.setter
    def second(self, value: int) -> None:
        pass

    @property
    def month(self) -> Union[RegisterParser[int], int]:
        return datetime.now().month

    @month.setter
    def month(self, value: int) -> None:
        pass

    @property
    def year(self) -> Union[RegisterParser[int], int]:
        return datetime.now().year

    @year.setter
    def year(self, value: int) -> None:
        pass

    def _prepare_update(self, value: datetime) -> None:
        # FIXME pycharm doesn't understand you can assign an int to the
        #  parser descriptors, but mypy does
        self.second = value.second
        self.minute = value.minute
        self.hour = value.hour
        self.day_of_month = value.day
        self.month = value.month
        self.year = value.year

    def _value(self) -> datetime:
        try:
            value = datetime(
                self.year,
                self.month,
                self.day_of_month,
                self.hour,
                self.minute,
                self.second,
            )
        except ValueError as err:
            raise ValueError(
                "Could not parse datetime. Perhaps the register state is"
                "invalid? Try setting to a known valid state first."
            ) from err
        return value
