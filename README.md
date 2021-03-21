# Frico - Framework for Integrated Circuits

Frico is a framework for interfacing with integrated circuits. It uses Python's
data descriptor functionality to present an interface similar to common
database ORMs like Django or SQLAlchemy. A device is defined as a class, the 
attributes of that class represent the types of data stored in the device's 
registers, and those attributes can be read or written on an instance of the 
device class with the framework managing IO.

## Installation

Frico is published on PyPI and is simple to install via pip, for example:

```shell
python3 -m pip install frico
```

Frico only supports Python 3 and includes type annotations.

If you want to contribute to Frico, you can set up a development environment
using the provided Makefile:
```shell
git clone git@github.com:mmangus/frico.git
cd frico
make
```

## Getting started

A Frico project will have three layers. Devices contain blocks and blocks 
contain parsers, like so:

```text
|==========================|
| Device                   |
|--------------------------|
|   RegisterBlockA         |
|..........................|
|     RegisterParser(0x00) |
|     RegisterParser(0x01) |
|--------------------------|
|   RegisterBlockB         |
|..........................|
|     RegisterParser(0x02) |
|     RegisterParser(0x03) |
|     ...etc               |
|--------------------------|
|   ...etc                 |
|==========================|
```

A chip is represented as a subclass of I2CDevice (SPIDevice coming soon), and
the data stored on of that chip is represented by subclasses of RegisterBlock.
A RegisterBlock can translate between a high-level Python object and a low-
level representation of that object in the device registers. Blocks use 
RegisterParsers to access specific addresses in the device registers and 
manipulate their values. 
 
Suppose you have a very simple real-time clock that keeps the current time
using 6 8-bit registers: second, minute, hour, day, month, and year (00-99), 
all encoded as binary-coded decimal (BCD) - the first nibble of 4 bits in 
each register is the 10s place and the second nibble is the 1s place, like 
this:

```text
|=======================================================================|
| Addr. | Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 |
|-------|-------------------------------|-------------------------------|
| 0x00  |      Seconds - tens           |         Seconds - ones        |
| 0x01  |      Minutes - tens           |         Minutes - ones        |
| 0x02  |        Hours - tens           |           Hours - ones        |
| 0x03  |          Day - tens           |             Day - ones        |
| 0x04  |        Month - tens           |           Month - ones        |
| 0x05  |         Year - tens           |            Year - ones        |
|=======================================================================|
```

Frico includes an abstract DatetimeRegisterBlock which lets you translate
datetime objects to/from the device's registers with minimal effort. Subclasses
of DatetimeRegisterBlock define attributes of type `RegisterParser[int]` to
map components of a datetime object to the values of specific register 
addresses. In this example, we can use the built-in BCDParser for almost
every register. The only exception is the year, which should have 2000 added 
to its value on read and subtracted from a given value on write.

```python
from datetime import datetime
from frico.blocks import DatetimeRegisterBlock
from frico.devices import I2CDevice
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


class RTC(I2CDevice):
    I2C_ADDRESS = 0x68  # the I2C device address
    I2C_READ_LEN = 0x06  # number of bytes readable from the device
    time = Time()


rtc = RTC()  # sets up I2C communication via SMBus
print(rtc.time)  # accesses the clock registers and prints a datetime
rtc.time = datetime.now()  # set the clock registers from a datetime
```
