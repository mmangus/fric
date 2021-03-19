# Frico - Framework for Integrated Circuits

Frico is a framework for interfacing with integrated circuits. It uses Python's
data descriptor functionality to present an interface similar to common
database ORMs like Django or SQLAlchemy. A device is defined as a class, the 
attributes of that class represent the types of data stored in the device's 
registers, and those attributes can be read or written on an instance of the 
device class with the framework managing IO.

## Installation

Frico is published on PyPI and is simple to install via pip, for example:

```python -m pip install frico```

Frico only supports Python 3 and includes type annotations.

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
using 6 registers: second, minute, hour, day, month, and year (00-99), all
encoded as binary-coded decimal (BCD) - the first nibble of 4 bits in each 
register is the 10s place and the second nibble is the 1s place, like this:

```text
|=======================================================================|
| Addr. | Bit 0 | Bit 1 | Bit 2 | Bit 3 | Bit 4 | Bit 5 | Bit 6 | Bit 7 |
|-------|-------------------------------|-------------------------------|
| 0x00  |      Seconds - tens           |         Seconds - ones        |
| 0x01  |      Minutes - tens           |         Minutes - ones        |
| 0x02  |        Hours - tens           |           Hours - ones        |
| 0x03  |          Day - tens           |             Day - ones        |
| 0x04  |        Month - tens           |           Month - ones        |
| 0x05  |         Year - tens           |            Year - ones        |
|=======================================================================|
```

Frico includes an abstract TimkeepingRegisterBlock which lets you translate
datetime objects to/from the device's registers with minimal effort. Subclasses
of TimekeepingRegisterBlock define attributes of type `RegisterParser[int]` to
map components of a datetime object to the values of specific register 
addresses. In this example, we can use the built-in BCDParser for everything.

```python
from datetime import datetime
from frico.blocks import TimekeepingRegisterBlock
from frico.devices import I2CDevice
from frico.parsers import BCDParser

# frico provides a TimekeepingRegisterBlock which reads and writes datetime, 
# with attributes to represent the individual time components
class Time(TimekeepingRegisterBlock):
    second = BCDParser(0x00)
    minute = BCDParser(0x01)
    hour = BCDParser(0x02)
    day_of_month = BCDParser(0x03)
    month = BCDParser(0x04)
    year = BCDParser(0x05)
    

class RTC(I2CDevice):
    I2C_ADDRESS = 0x68  # the I2C device address
    I2C_READ_LEN = 0x06  # number of bytes readable from the device
    time = Time()

    
rtc = RTC()  # sets up I2C communication via SMBus
rtc.time = datetime.now()  # sets the clock registers from a datetime
print(rtc.time)  # accesses the clock registers and prints a datetime
```
