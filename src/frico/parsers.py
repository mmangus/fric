from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Tuple, Type, TypeVar, Union

from .bitstring import BitString
from .typing import RegisterState

if TYPE_CHECKING:
    from .blocks import RegisterBlock


ParserType = TypeVar("ParserType")


class RegisterParser(ABC, Generic[ParserType]):
    """
    Abstract base class for data descriptors that parse/set register values.
    Subclasses represent the various formats of registers used by a Device.
    """

    def __init__(self, address: Union[int, slice]):
        """
        Initialize a parser instance for the given register address(es).

        Parameters
        ----------
        address : Union[int, slice]
            An index or slice to retrieve byte(s) at a given address
        """
        if isinstance(address, int):
            address = slice(address, address + 1)
        self._address = address
        # FIXME if there are multiple instances of a given RegisterBlock
        #  class, all their parsers will access the same state! this could
        #  cause weird behavior; store state in a dict keyed by instance?
        #  or use a meta-class to define a label?
        #  https://nbviewer.jupyter.org/urls/gist.github.com/ChrisBeaumont/5758381/raw/descriptor_writeup.ipynb#Make-sure-to-keep-instance-level-data-instance-specific
        self._register_state: RegisterState = []

    def __get__(
        self,
        instance: "RegisterBlock[Any]",
        owner: Type["RegisterBlock[Any]"],
    ) -> ParserType:
        """
        When accessing a RegisterParser, set its register state based on the
        state of the RegisterBlock instance that it belongs to (which in turn
        reads from the I2CDevice instance /it/ belongs to). See note in
        RegisterBlock.__get__ about why this behavior is needed.
        """
        self._register_state = instance.register_state
        return self._value()

    def __set__(
        self, instance: "RegisterBlock[Any]", value: ParserType
    ) -> None:
        """
        When setting a RegisterParser value, make sure its state is in sync
        with all pending changes to the RegisterBlock instance that it belongs
        to, then update the pending state with changes from this parser.
        """
        self._register_state = instance.pending_state
        new_state = self._prepare_update(value)
        instance.update_register_state(self._address, new_state)

    @abstractmethod
    def _prepare_update(self, value: ParserType) -> RegisterState:
        """
        Subclasses should implement a _prepare_update method which returns a
        register address offset (index or slice) and a list of BitStrings to
        replace the data currently at the address(es).
        """

    @abstractmethod
    def _value(self) -> ParserType:
        """
        Subclasses should implement a _value method which returns an object
        of the appropriate type to represent the register content
        """

    @property
    def _local_bytes(self) -> RegisterState:
        """
        Returns a slice of the register state with just those bytes needed for
        an instance to do its parsing.
        """
        return self._register_state[self._address]


class BCDParser(RegisterParser[int]):
    """
    Base class for registers with simple BCD format. Subclasses can define a
    class attribute `bcd_bounds` with a tuple of (start, stop) tuples (i.e. a
    tuple representing the bits to slice for each digit). By default, parses
    2 decimal digits from the 4-bit nibbles of a byte.
    """

    bcd_bounds: Tuple[Tuple[int, int], ...] = ((0, 4), (4, 8))

    def _value(self) -> int:
        return self._local_bytes[0].decode_bcd(*self.bcd_bounds)

    def _prepare_update(self, value: int) -> RegisterState:
        offset = min(s[0] for s in self.bcd_bounds)
        sizes = [s[1] - s[0] for s in self.bcd_bounds]
        new_bitstring = BitString.encode_bcd(value, sizes)
        new_state = [self._local_bytes[0].replace(offset, new_bitstring)]
        return new_state


class FlagParser(RegisterParser[bool]):
    """
    Base class for flags stored as a single bit in a register.
    """

    def __init__(self, address: int, bit: int) -> None:
        # FIXME better as extra arg to constructor or class-level attribute?
        #  for BCDParser, its nice to have subclasses define their bounds
        #  in a way that can be reused across multiple registers. i'm not sure
        #  there is an equivalent use case for FlagParser, but there could
        #  be. it feels weird for them to implement very similar functionality
        #  in 2 different ways.
        self._bit = bit
        super().__init__(address)

    def _value(self) -> bool:
        return bool(self._local_bytes[0][self._bit])

    def _prepare_update(self, value: bool) -> RegisterState:
        new_state = [
            self._local_bytes[0].replace(self._bit, BitString(int(value)))
        ]
        return new_state
