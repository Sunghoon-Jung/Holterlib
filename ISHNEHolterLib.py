#!/usr/bin/env python3

"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

import os
import numpy as np
import datetime
import sys
from PyCRC.CRCCCITT import CRCCCITT

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

#################################### Class: ####################################

class Holter:
    def __init__(self, filename):
        self.filename = filename
        self.data = None
        self.load_header()
        if not self.is_valid():
            print( "Warning: file appears to be invalid or corrupt." )

    def load_header(self):
        filename = self.filename
        assert os.path.getsize(filename) >= 522, "File is too small to be an ISHNE Holter."

        self.magic_number = get_val(filename, 0, 'a8')
        self.checksum = get_val(filename, 8, np.uint16)
        #print( "Checksum in file: %s" % ckstr(self.checksum) )

        # Fixed-size part of header:
        self.var_block_size   =   get_long_int(filename,  10)
        self.ecg_size         =   get_long_int(filename,  14)  # in number of samples
        self.var_block_offset =   get_long_int(filename,  18)  # start of variable-length block
        self.ecg_block_offset =   get_long_int(filename,  22)  # start of ECG samples
        self.file_version     =  get_short_int(filename,  26)
        self.first_name       =        get_val(filename,  28, 'a40')
        self.last_name        =        get_val(filename,  68, 'a40')
        self.id               =        get_val(filename, 108, 'a20')
        self.sex              =  get_short_int(filename, 128)  # 1=male, 2=female
        self.race             =  get_short_int(filename, 130)  # 1=white, 2=black, 3=oriental
        self.birth_date       =   get_datetime(filename, 132)
        self.record_date      =   get_datetime(filename, 138)  # recording date
        self.file_date        =   get_datetime(filename, 144)  # date of creation of output file
        self.start_time       =   get_datetime(filename, 150, time=True)  # start time of Holter
        self.nleads           =  get_short_int(filename, 156)
        self.lead_spec        = [get_short_int(filename, 158+i*2) for i in range(12)]
        self.lead_quality     = [get_short_int(filename, 182+i*2) for i in range(12)]
        self.ampl_res         = [get_short_int(filename, 206+i*2) for i in range(12)]  # lead resolution in nV
        self.pm               =  get_short_int(filename, 230)  # pacemaker
        self.recorder_type    =        get_val(filename, 232, 'a40')  # analog or digital
        self.sr               =  get_short_int(filename, 272)  # sample rate in Hz
        self.proprietary      =        get_val(filename, 274, 'a80')
        self.copyright        =        get_val(filename, 354, 'a80')
        self.reserved         =        get_val(filename, 434, 'a88')

        # Variable-length part of header:
        if self.var_block_size > 0:
            self.var_block = get_val(filename, 522, 'a'+str(self.var_block_size))
        else:
            self.var_block = None

    def load_data(self):
        """This may take some time and memory, so we don't do it until we're asked.  The
        'data' variable is a numpy array indexed as data[lead][sample_number],
        with values stored in mV.
        """
        # Get the data:
        with open(self.filename, 'rb') as f:
            f.seek(self.var_block_offset, os.SEEK_SET)
            self.data = np.fromfile(f, dtype=np.int16)
        # Convert it to a 2D array of floats, cropping the end if necessary:
        nleads = self.nleads
        self.data = np.reshape(self.data[:len(self.data)/nleads*nleads],
                               (nleads, len(self.data)/nleads), order='F')
        self.data = self.data.astype(float)
        # Convert measurements to mV:
        for i in range(len(self.data)):  # i = lead
            self.data[i] /= 1e6/self.ampl_res[i]

    def compute_checksum(self):
        """Note: this operates on the file on disk (pointed to by self.filename), *not*
        the current data structure in memory.
        """
        with open(self.filename, 'rb') as f:
            f.seek(10, os.SEEK_SET)
            header_block = np.fromfile(f, dtype=np.uint8, count=self.ecg_block_offset-10)
        return np.uint16( CRCCCITT(version='FFFF').calculate(header_block.tostring()) )
        # tostring() is just to turn it into a bytearray
        # Another method to do the calculation:
        #   from crccheck.crc import Crc16CcittFalse
        #   Crc16CcittFalse.calc( header )

    def is_valid(self, verify_checksum=True):
        """Check for obvious problems with the file: wrong file signature, bad checksum,
        or invalid values for file or header size.
        """
        if self.magic_number != b'ISHNE1.0':
            #print ("magic fail")  # debugging
            return False
        if self.var_block_offset != 522:
            #print ("offset fail")  # debugging
            return False
        filesize = os.path.getsize(self.filename)
        expected = 522 + self.var_block_size + 2*self.ecg_size
        if filesize!=expected:
            # ecg_size may have been reported as samples per lead instead of
            # total number of samples
            expected += 2*self.ecg_size*(self.nleads-1)
            if filesize!=expected:
                #print ("size fail")  # debugging
                return False
        if verify_checksum and (self.checksum != self.compute_checksum()):
                #print ("checksum fail")  # debugging
                return False
        return True  # didn't find any problems above

    def get_leadspec(self, lead):
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

    # TODO: dictionaries for gender and race?

    def write_file(self, overwrite=False):
        """This function will write the object to disk as an ISHNE Holter file.  You do
        *not* need to set the following variables: magic_number, checksum,
        var_block_size, ecg_size, var_block_offset, ecg_block_offset, and file_date.

        By default, it will not overwrite an existing file.

        This is the only function in the class that requires python3, for to_bytes().
        """
        if os.path.exists(self.filename):
            assert overwrite, "File with that name already exists."
            os.remove(self.filename)  # overwrite is enabled; rm the existing
                                      # file before we start (note: may fail if
                                      # it's a directory not a file)
        try:
            var_block_size = len( self.var_block )
        except TypeError:
            var_block_size = 0
        try:
            ecg_size = len( self.data[0] )
            # it's not clear if we should report the total number of samples
            # for *one* lead, or for *all* leads.  we do the former.
        except TypeError:
            ecg_size = 0

        with open(self.filename, 'ab') as f:
            f.write( b'ISHNE1.0' )
            f.write( b'\x00\x00' )  # TODO: checksum
            f.write( (var_block_size            ).to_bytes(4, sys.byteorder) )
            f.write( (ecg_size                  ).to_bytes(4, sys.byteorder) )
            f.write( (522                       ).to_bytes(4, sys.byteorder) )
            f.write( (522+var_block_size        ).to_bytes(4, sys.byteorder) )
            f.write( (self.file_version         ).to_bytes(2, sys.byteorder) )
            f.write( self.first_name          [:40].ljust(40, b'\x00') )
            f.write( self.last_name           [:40].ljust(40, b'\x00') )
            f.write( self.id                  [:20].ljust(20, b'\x00') )
            f.write( (self.sex                  ).to_bytes(2, sys.byteorder) )
            f.write( (self.race                 ).to_bytes(2, sys.byteorder) )
            if self.birth_date:
                f.write( (self.birth_date.day   ).to_bytes(2, sys.byteorder) )
                f.write( (self.birth_date.month ).to_bytes(2, sys.byteorder) )
                f.write( (self.birth_date.year  ).to_bytes(2, sys.byteorder) )
            else:
                f.write( (0                     ).to_bytes(6, sys.byteorder) )
            if self.record_date:
                f.write( (self.record_date.day  ).to_bytes(2, sys.byteorder) )
                f.write( (self.record_date.month).to_bytes(2, sys.byteorder) )
                f.write( (self.record_date.year ).to_bytes(2, sys.byteorder) )
            else:
                f.write( (0                     ).to_bytes(6, sys.byteorder) )
            today = datetime.datetime.now().date()
            f.write( (today.day                 ).to_bytes(2, sys.byteorder) )
            f.write( (today.month               ).to_bytes(2, sys.byteorder) )
            f.write( (today.year                ).to_bytes(2, sys.byteorder) )
            if self.start_time:
                f.write( (self.start_time.hour  ).to_bytes(2, sys.byteorder) )
                f.write( (self.start_time.minute).to_bytes(2, sys.byteorder) )
                f.write( (self.start_time.second).to_bytes(2, sys.byteorder) )
            else:
                f.write( (0                     ).to_bytes(6, sys.byteorder) )
            f.write( (self.nleads               ).to_bytes(2, sys.byteorder) )
            for i in range(12):
                f.write( (self.lead_spec[i]     ).to_bytes(2, sys.byteorder) )
            for i in range(12):
                f.write( (self.lead_quality[i]  ).to_bytes(2, sys.byteorder) )
            for i in range(12):
                f.write( (self.ampl_res[i]      ).to_bytes(2, sys.byteorder) )
            f.write( (self.pm                   ).to_bytes(2, sys.byteorder) )
            f.write( self.recorder_type       [:40].ljust(40, b'\x00') )
            f.write( (self.sr                   ).to_bytes(2, sys.byteorder) )
            f.write( self.proprietary         [:80].ljust(80, b'\x00') )
            f.write( self.copyright           [:80].ljust(80, b'\x00') )
            f.write( self.reserved            [:88].ljust(88, b'\x00') )
            if var_block_size > 0:
                f.write(self.var_block)

            # TODO: save data block here
            # TODO: handle negative values (to_bytes tries to make unsigned by default)

################################################################################
