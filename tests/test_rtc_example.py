from datetime import datetime

from frico.bitstring import BitString
from frico.blocks import DatetimeRegisterBlock
from frico.devices import FakeDevice
from frico.parsers import BCDParser
from frico.typing import RegisterState


class YearParser(BCDParser):
    def _value(self) -> int:
        return super()._value() + 2000

    def _prepare_update(self, value: int) -> RegisterState:
        value -= 2000
        return super()._prepare_update(value)


class Time(DatetimeRegisterBlock):
    second = BCDParser(0x00)
    minute = BCDParser(0x01)
    hour = BCDParser(0x02)
    day_of_month = BCDParser(0x03)
    month = BCDParser(0x04)
    year = YearParser(0x05)


class RTC(FakeDevice):
    time = Time()


def test_get_datetime():
    """Test reading a datetime from register state"""
    rtc = RTC()
    # this test sets state directly instead of as a datetime
    rtc.write_registers(
        [
            BitString.encode_bcd(11),
            BitString.encode_bcd(0),
            BitString.encode_bcd(21),
            BitString.encode_bcd(20),
            BitString.encode_bcd(3),
            BitString.encode_bcd(21),
        ]
    )
    # make sure the RTC matches the intended state
    assert rtc.time == datetime(
        second=11, minute=0, hour=21, day=20, month=3, year=2021
    ), "Datetime does not match intended initial state"


def test_set_datetime():
    """Test updating the clock by setting the time attribute to a datetime."""
    rtc = RTC()
    # start with an empty register state
    rtc.write_registers([BitString(0, fill=8)] * 6)
    now = datetime.now().replace(
        microsecond=0
    )  # microseconds will not be stored
    rtc.time = now
    assert rtc.time == now, "Read a different state than was written"
