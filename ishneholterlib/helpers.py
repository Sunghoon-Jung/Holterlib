import os
import sys
import math
import numpy as np
import datetime
from .constants import lead_specs, lead_qualities

########################## reading values from file: ###########################

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

###################### preparing to write values to file: ######################

def bytes_from_datetime(dt):
    """Convert a datetime back into a sequence of bytes, e.g. when writing a header
    back to disk.

    Keyword arguments:
    dt -- date or time object (or None)
    """
    dt_bytes = bytearray()
    if type(dt) == datetime.date:
        dt_bytes += (dt.day   ).to_bytes(2, sys.byteorder)
        dt_bytes += (dt.month ).to_bytes(2, sys.byteorder)
        dt_bytes += (dt.year  ).to_bytes(2, sys.byteorder)
    elif type(dt) == datetime.time:
        dt_bytes += (dt.hour  ).to_bytes(2, sys.byteorder)
        dt_bytes += (dt.minute).to_bytes(2, sys.byteorder)
        dt_bytes += (dt.second).to_bytes(2, sys.byteorder)
    elif dt == None:
        dt_bytes += (0        ).to_bytes(6, sys.byteorder)
        # TODO?: -9s instead of 0s
    else:
        raise TypeError("dt must be datetime.date, datetime.time, or None.")
    return dt_bytes

def bytes_from_lead_names(leads):
    spec_bytes = bytearray()
    for l in leads:
        spec = val_to_key(lead_specs, l.name, 0)
        spec_bytes += (spec).to_bytes(2, sys.byteorder, signed=True)
    for i in range(12-len(leads)):
        spec_bytes += (-9  ).to_bytes(2, sys.byteorder, signed=True)
    return spec_bytes

def bytes_from_lead_qualities(leads):
    qual_bytes = bytearray()
    for l in leads:
        try:    q = l.notes['quality']
        except: q = None
        q = val_to_key(lead_qualities, q, 0)
        qual_bytes += (q ).to_bytes(2, sys.byteorder, signed=True)
    for i in range(12-len(leads)):
        qual_bytes += (-9).to_bytes(2, sys.byteorder, signed=True)
    return qual_bytes

def bytes_from_lead_resolutions(leads):
    res_bytes = bytearray()
    res = lead_resolutions_nv(leads)
    for r in res:
        res_bytes += (r ).to_bytes(2, sys.byteorder, signed=True)
    for i in range(12-len(leads)):
        res_bytes += (-9).to_bytes(2, sys.byteorder, signed=True)
    return res_bytes

def lead_resolutions_nv(leads):
    resolutions = []
    for l in leads:
        try:
            res = int(1e6/l.original_umV)
        except:
            # handle the case where l.umV is not set.  there are many ways to do
            # this; i simply divide the used range among the 16 bits.  TODO: do
            # a better job.... need to preserve values (hard with scaling and
            # interp), maybe preserve zero, set range based on statistical
            # outliers, etc.
            full_range_mv = max(l.ampl) - min(l.ampl)
            res = math.ceil(1e6 * full_range_mv / 2**16)
        resolutions.append(res)
    return resolutions

def val_to_key(d, v, default_k):
    """Return 'the' key associated with value v in dictionary d, or default_k if not
    found.

    Keyword arguments:
    d -- dict to search
    v -- value to search for
    """
    if v in d.values():
        for key,val in d.items():
            if val==v:
                return key
    else:
        return default_k

#################################### other: ####################################

def ckstr(checksum):
    """Return a value as e.g. 'FC8E', i.e. an uppercase hex string with no leading
    '0x' or trailing 'L'.
    """
    return hex(checksum)[2:].rstrip('L').upper()

################################################################################
