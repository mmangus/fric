from typing import Collection, Tuple, Union


class BitString(int):
    """
    Given a binary string or positive integer, store the value as an integer
    which can be sliced or concatenated based on the string representation.

    Useful for working with binary-coded decimal values where, for example,
    each 4-bit nibble of a byte is used to represent a decimal digit - see
    `BitString.encode_bcd` and `BitString.decode_bcd`.

    >>> BitString(10, fill=8)
    BitString('00001010')
    >>> BitString('1010') + BitString('1010') == 20
    True
    >>> BitString('1010').join(BitString('1010')) == 170
    True
    >>> BitString(10)[:2]
    BitString('10')
    >>> BitString.concat(BitString('1'), BitString.encode_bcd(24, (3, 4)))
    BitString('10100100')
    >>> BitString('10100100').decode_bcd((1, 4), (4, 8))
    24
    """

    bitstring: str  # signal to mypy that this will be added by __new__

    def __new__(
        cls,
        value: Union[str, int],
        fill: int = 0,
        raise_on_overflow: bool = False,
    ) -> "BitString":
        """
        Accepts a positive integer or string representation of a binary
        unsigned integer. Stores the binary string representation.

        Parameters
        ----------
        value : Union[str, int]
            A positive integer or its binary string representation
        fill : int, default 0
            The minimum length of the bitstring (will pad with 0s on the left).
            Note that if you pass in a string, BitString will always maintain
            at least the length of the string you input.

        raise_on_overflow : bool, default False
            Whether to raise ValueError if fill is non-zero and the value
            cannot be represented by the number of bits specified by fill
        """
        if isinstance(value, str):
            # make the fill value at least as long as the input
            fill = max(len(value), fill)
            value = int(value.replace(" ", ""), 2)
        if value < 0:
            raise ValueError("BitString does not support negative values")
        instance = super().__new__(cls, value)
        bitstring = bin(instance)[2:]
        instance.bitstring = bitstring.zfill(fill)
        if raise_on_overflow and len(instance.bitstring) > fill:
            raise ValueError(f"Value {value} too large for {fill} bits")
        return instance

    def __getitem__(self, key: Union[int, slice]) -> "BitString":
        """
        Slice the string representation

        >>> BitString('1010')[:2]
        BitString('10')
        """
        slice_ = self.bitstring[key]
        return BitString(slice_, fill=len(slice_))

    def replace(self, offset: int, value: "BitString") -> "BitString":
        """
        Return a new BitString where `len(value)` bits starting at `offset`
        are replaced by `value`.

        >>> BitString('1000').replace(1, BitString('101'))
        BitString('1101')
        >>> BitString('1111').replace(2, BitString('0'))
        BitString('1101')
        """
        if len(str(value)) > len(str(self)[offset:]):
            raise ValueError("Value too large for requested offset")
        bit_list = list(self.bitstring)
        to_insert = str(value)
        bit_list[offset : offset + len(to_insert)] = to_insert
        return BitString("".join(bit_list))

    @classmethod
    def concat(cls, *bitstrings: "BitString") -> "BitString":
        """
        Concatenate two or more BitStrings together as strings to produce a new
        BitString

        Parameters
        ----------
        *bitstrings : BitString

        >>> BitString.concat(BitString('10'), BitString('10'))
        BitString('1010')
        """
        if any(b for b in bitstrings if not isinstance(b, BitString)):
            raise TypeError("BitString.concat only operates on BitStrings")
        concatenated_string = "".join(map(str, bitstrings))
        return BitString(concatenated_string, fill=len(concatenated_string))

    def join(self, *others: "BitString") -> "BitString":
        """
        Join the string representation of other BitStrings onto this one.

        Note that unlike str.join, this method is variadic.

        Parameters
        ----------
        *others: BitString

        >>> BitString('10').join(BitString('10'), BitString('01'))
        BitString('101001')
        """
        return BitString.concat(self, *others)

    def decode_bcd(self, *bounds: Tuple[int, int]) -> int:
        """
        Given bounds of each digit, slice the BitString to produce a place-value
        decimal number from those slices. First bound is most-significant bit.

        Parameters
        ----------
        * bounds: Tuple[int, int]
            The boundaries for each digit. Must be castable to a `slice`.

        >>> BitString('10011001').decode_bcd((0, 4), (4, 8))
        99
        >>> BitString('10011001').decode_bcd((1, 4), (4, 8))
        19
        >>> BitString('10011001').decode_bcd((4, 8), (1, 4))
        91
        """
        if not bounds:
            raise ValueError("must pass at least one bound to decode BCD")
        digits = [self[slice(*b)] for b in bounds]
        return sum(10 ** i * d for i, d in enumerate(digits[::-1]))

    @classmethod
    def encode_bcd(
        cls, value: int, sizes: Collection[int] = (4, 4)
    ) -> "BitString":
        """
        Given a decimal value and a tuple of sizes (number of bits) for each
        digit, return a BitString with BCD encoding of that value. Defaults to
        8-bit encoding of 2 decimal digits in 4 bits each.

        Parameters
        ----------
        value: int
            The decimal value to encode
        sizes: Iterable[int, ...], default (4, 4)
            The number of bits to use to encode each digit

        >>> BitString.encode_bcd(19)
        BitString('00011001')
        >>> BitString.encode_bcd(19, (3, 4))
        BitString('0011001')
        """
        if not isinstance(value, int) or value < 0:
            raise TypeError("Can only encode a positive (unsigned) int")
        n_digits = len(sizes)
        string_value = str(value).zfill(n_digits)
        if len(string_value) > n_digits:
            raise ValueError(
                f"Value {value} too large for number of digits implied by "
                f"sizes ({n_digits})."
            )
        return BitString.concat(
            *(
                BitString(int(digit), fill=bits, raise_on_overflow=True)
                for digit, bits in zip(string_value, sizes)
            )
        )

    def __repr__(self) -> str:
        return f"BitString('{self.bitstring}')"

    def __str__(self) -> str:
        return self.bitstring
