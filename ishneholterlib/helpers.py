import os
import numpy as np
import datetime

def get_val(filename, ptr, datatype):
    """Jump to position 'ptr' in file and read a value of a given type (e.g. int16)."""
    val = None
    with open(filename, 'rb') as f:
        f.seek(ptr, os.SEEK_SET)
        val = np.fromfile(f, dtype=datatype, count=1)
        val = val[0]
    return val

def get_short_int(filename, ptr):
    """Jump to position 'ptr' in file and read a 16-bit integer."""
    val = get_val(filename, ptr, np.int16)
    return int( val )

def get_long_int(filename, ptr):
    """Jump to position 'ptr' in file and read a 32-bit integer."""
    val = get_val(filename, ptr, np.int32)
    return int( val )

def get_datetime(filename, offset, time=False):
    """Read three consecutive 16-bit values from file and interpret them as (day,
    month, year) or (hour, minute, second).  Return a date or time object.

    Keyword arguments:
    filename -- file to read
    offset -- start address of first value in file
    time -- True if we're getting (h,m,s), False if we're getting (d,m,y)
    """
    a,b,c = [get_short_int(filename, offset+2*i) for i in range(3)]
    try:
        if time:
            output = datetime.time(a,b,c)
        else:
            output = datetime.date(c,b,a)
    except ValueError:
        output = None
    return output

def ckstr(checksum):
    """Return a value as e.g. 'FC8E', i.e. an uppercase hex string with no leading
    '0x' or trailing 'L'.
    """
    return hex(checksum)[2:].rstrip('L').upper()
