#!/usr/bin/env python

"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

import os
import numpy as np
import datetime

################################## Functions: ##################################

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

def ckstr(checksum):
    """Return a value as e.g. 'FC8E', i.e. an uppercase hex string with no leading
    '0x' or trailing 'L'.
    """
    return hex(checksum)[2:].rstrip('L').upper()

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

################################### Classes: ###################################

class Holter:
    def __init__(self, filename):
        self.filename = filename
        self.header = Header(filename)
        self.data = None
        if not self.is_valid():
            print( "Warning: file appears to be invalid or corrupt." )

    def load_data(self):
        """This may take some time and memory, so we don't do it until we're asked.  The
        'data' variable is a numpy array indexed as data[lead][sample_number],
        with values stored in mV.
        """
        # Get the data:
        with open(self.filename, 'rb') as f:
            f.seek(self.header.var_block_offset, os.SEEK_SET)
            self.data = np.fromfile(f, dtype=np.int16)
        # Convert it to a 2D array of floats, cropping the end if necessary:
        nleads = self.header.nleads
        self.data = np.reshape(self.data[:len(self.data)/nleads*nleads],
                               (nleads, len(self.data)/nleads), order='F')
        self.data = self.data.astype(float)
        # Convert measurements to mV:
        for i in range(len(self.data)):  # i = lead
            self.data[i] /= 1e6/self.ampl_res[i]

    def is_valid(self):
        """Check for obvious problems with the file: wrong file signature, or
        invalid values for file or header size.  CRC is not yet being checked.
        """
        if self.header.magic_number != 'ISHNE1.0':
            return False
        if self.header.var_block_offset != 522:
            return False
        filesize = os.path.getsize(self.filename)
        expected = 522 + self.header.var_block_size + 2*self.header.ecg_size
        if filesize!=expected:
            # ecg_size may have been reported as samples per lead instead of
            # total number of samples
            expected += 2*self.header.ecg_size*(self.header.nleads-1)
            if filesize!=expected:
                return False
        # TODO: validate checksum here and return False if it fails.  some libs
        # that should be able to do it:
        #   from PyCRC.CRCCCITT import CRCCCITT
        #   from crccheck.crc import Crc16Ccitt
        return True  # didn't find any problems above

class Header:

    def __init__(self, filename):
        assert os.path.getsize(filename) >= 522, "File is too small to be an ISHNE Holter."

        self.magic_number = get_val(filename, 0, 'a8')
        self.checksum = get_val(filename, 8, np.uint16)
        #print( "Checksum in file: %s" % ckstr(self.checksum) )

        # Fixed-size part of header:
        self.var_block_size   = get_long_int(filename, 10)
        self.ecg_size         = get_long_int(filename, 14)    # in number of samples
        self.var_block_offset = get_long_int(filename, 18)    # start of variable-length block
        self.ecg_block_offset = get_long_int(filename, 22)    # start of ECG samples
        self.file_version     = get_short_int(filename, 26)
        self.first_name       = get_val(filename, 28, 'a40')
        self.last_name        = get_val(filename, 68, 'a40')
        self.id               = get_val(filename, 108, 'a20')
        self.sex              = get_short_int(filename, 128)  # 1=male, 2=female
        self.race             = get_short_int(filename, 130)  # 1=white, 2=black, 3=oriental
        self.birth_date       = get_datetime(filename, 132)
        self.record_date      = get_datetime(filename, 138)   # recording date
        self.file_date        = get_datetime(filename, 144)   # date of creation of output file
        self.start_time       = get_datetime(filename, 150, time=True)  # start time of Holter
        self.nleads           = get_short_int(filename, 156)
        self.lead_spec        = [get_short_int(filename, 158+i*2) for i in range(12)]
        self.lead_quality     = [get_short_int(filename, 182+i*2) for i in range(12)]
        self.ampl_res         = [get_short_int(filename, 206+i*2) for i in range(12)]  # lead resolution in nV
        self.pm               = get_short_int(filename, 230)  # pacemaker
        self.recorder_type    = get_val(filename, 232, 'a40') # analog or digital
        self.sr               = get_short_int(filename, 272)  # sample rate in Hz
        self.proprietary      = get_val(filename, 274, 'a80')
        self.copyright        = get_val(filename, 354, 'a80')
        self.reserved         = get_val(filename, 434, 'a88')

        # Variable-length part of header:
        if self.var_block_size > 0:
            self.var_block = get_val(filename, 522, 'a'+str(self.var_block_size))
        else:
            self.var_block = None

    def leadspec(self, lead):
        """Convert lead number (0-indexed) into name (such as 'V1')."""
        lead_specs = {
            -9: 'absent', 0: 'unknown', 1: 'generic',
            2: 'X',    3: 'Y',    4: 'Z',
            5: 'I',    6: 'II',   7: 'III',
            8: 'aVR',  9: 'aVL', 10: 'aVF',
            11: 'V1', 12: 'V2',  13: 'V3',
            14: 'V4', 15: 'V5',  16: 'V6',
            17: 'ES', 18: 'AS',  19: 'AI'
        }
        return lead_specs[self.lead_spec[lead]]

    # lead_quals = {
    #     -9: 'absent',
    #     0: 'unknown',
    #     1: 'good',
    #     2: 'intermittent noise',
    #     3: 'frequent noise',
    #     4: 'intermittent disconnect',
    #     5: 'frequent disconnect'
    # }

    # pm_codes = {
    #     0: 'none',
    #     1: 'unknown type',
    #     2: 'single chamber unipolar',
    #     3: 'dual chamber unipolar',
    #     4: 'single chamber bipolar',
    #     5: 'dual chamber bipolar',
    # }

    # TODO?: merge Header back into Holter class

class Subject:
    pass  # TODO?  this would hold static subject info from header.  so we can
          # do stuff like holter.subject.is_male, holter.subject.name, etc.

################################################################################
