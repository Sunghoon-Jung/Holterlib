#!/usr/bin/env python

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

class Holter:
    def __init__(self, filename):
        self.filename = filename
        self.header = Header(filename)
        self.data = None
        if not self.is_valid():
            print( "Warning: file appears to be invalid or corrupt." )

    def load_data(self):
        """This may take some time and memory, so we don't do it until we're asked."""
        self.data = Data()

    def is_valid(self):
        """Check for obvious problems with the file, namely failing header checksum,
        wrong file signature, or invalid values for file or header size.
        """
        if self.header.magic_number != 'ISHNE1.0':
            return False
        if self.header.var_block_offset != 522:
            return False
        if False:  # TODO: validate checksum
            return False
        if False:         # TODO: check size of file compared to expected size.  note
            return False  # that ecg_size may be reported as size per lead OR total size.
        return True  # didn't find any problems above


# // If Sample_Size_ECG is total number of samples:
# //     int samples_per_lead = m_ISHNEHeader.Sample_Size_ECG / m_ISHNEHeader.nLeads;
# // If Sample_Size_ECG is number of samples for a single lead:
# //     int samples_per_lead = m_ISHNEHeader.Sample_Size_ECG;
# // If Sample_Size_ECG is unreliable/nonsense:
# int samples_per_lead = (file_size - m_ISHNEHeader.Offset_ECG_block) / m_ISHNEHeader.nLeads / 2;
# m_ISHNEData.data = new short*[m_ISHNEHeader.nLeads];  // 1st dimension
# for(i = 0; i < m_ISHNEHeader.nLeads; i++) {
#   m_ISHNEData.data[i] = new short[samples_per_lead];  // 2nd dimension
# }
# m_ISHNEData.nLeads = m_ISHNEHeader.nLeads;
# m_ISHNEData.samples_per_lead = samples_per_lead;


class Header:

    # lead_specs = {
    #     -9: 'absent', 0: 'unknown', 1: 'generic',
    #     2: 'X',    3: 'Y',    4: 'Z',
    #     5: 'I',    6: 'II',   7: 'III',
    #     8: 'aVR',  9: 'aVL', 10: 'aVF',
    #     11: 'V1', 12: 'V2',  13: 'V3',
    #     14: 'V4', 15: 'V5',  16: 'V6',
    #     17: 'ES', 18: 'AS',  19: 'AI'
    # }

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

    def __init__(self, filename):
        assert os.path.getsize(filename) >= 522, "File is too small to be an ISHNE Holter."

        self.magic_number = get_val(filename, 0, 'a8')
        self.checksum = get_short_int(filename, 8)

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
            # TODO?: keep as binary, not string
        else:
            self.var_block = None

class Subject:
    pass  # TODO?  this would hold static subject info from header.  so we can
          # do stuff like holter.subject.is_male, holter.subject.name, etc.

class Data:  # TODO: this holds the actual samples
    pass
