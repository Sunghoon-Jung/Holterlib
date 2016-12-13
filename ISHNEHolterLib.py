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

################################### Classes: ###################################

class Holter:
    def __init__(self, filename):
        self.filename = filename
        self.load_header()
        if not self.is_valid():
            print( "Warning: file appears to be invalid or corrupt." )
        # else:
        #     print( "Loaded header successfully.  Remember to run load_data() if you need the data too." )
        # TODO: set up for creating a *new* Holter, not just loading an existing one from a file

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
        lead_spec             = [get_short_int(filename, 158+i*2) for i in range(12)]
        lead_quality          = [get_short_int(filename, 182+i*2) for i in range(12)]
        ampl_res              = [get_short_int(filename, 206+i*2) for i in range(12)]  # lead resolution in nV
        self.pm               =  get_short_int(filename, 230)  # pacemaker
        self.recorder_type    =        get_val(filename, 232, 'a40')  # analog or digital
        self.sr               =  get_short_int(filename, 272)  # sample rate in Hz
        self.proprietary      =        get_val(filename, 274, 'a80')
        self.copyright        =        get_val(filename, 354, 'a80')
        self.reserved         =        get_val(filename, 434, 'a88')
        # TODO?: read all the above with one open()

        # Variable-length part of header:
        if self.var_block_size > 0:
            self.var_block = get_val(filename, 522, 'a'+str(self.var_block_size))
        else:
            self.var_block = None

        # TODO?: terminate strings read above at first \x00

        # Create array of Leads (where lead specs and data will be stored):
        self.lead = [None for _ in range(self.nleads)]
        for i in range(self.nleads):
            self.lead[i] = Lead(lead_spec[i], lead_quality[i], ampl_res[i])

    def load_data(self):
        """This may take some time and memory, so we don't do it until we're asked.  The
        'lead' variable is a list of Lead objects where lead[i].data is the data
        for lead number i.
        """
        # Get the data:
        with open(self.filename, 'rb') as f:
            f.seek(self.var_block_offset, os.SEEK_SET)
            data = np.fromfile(f, dtype=np.int16)
        # Convert it to a 2D array, cropping the end if necessary:
        nleads = self.nleads
        data = np.reshape( data[:int(len(data)/nleads)*nleads],
                                (nleads, int(len(data)/nleads)),
                                order='F' )
        # Save each row (lead), converting measurements to mV in the process:
        for i in range(nleads):
            self.lead[i].save_data( data[i] )

    def compute_checksum(self, header_block=None):
        """Compute checksum of header block.  If header_block is None, it operates on
        the file on disk (pointed to by self.filename).

        Keyword arguments:
        header_block -- a bytes object containing the ISHNE header (typically bytes 10-522 of the file)
        """
        if header_block == None:
            with open(self.filename, 'rb') as f:
                f.seek(10, os.SEEK_SET)
                header_block = np.fromfile(f, dtype=np.uint8, count=self.ecg_block_offset-10)
                header_block = header_block.tostring()  # to make it a bytes object
        return np.uint16( CRCCCITT(version='FFFF').calculate(header_block) )
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
        # TODO?: check SR > 0
        return True  # didn't find any problems above

    def get_length(self):
        """Return the length of the (first lead of the) Holter as a timedelta object."""
        return datetime.timedelta(seconds = 1.0 * len(self.lead[0].data) / self.sr)

    # TODO?:
    # pm_codes = {
    #     0: 'none',
    #     1: 'unknown type',
    #     2: 'single chamber unipolar',
    #     3: 'dual chamber unipolar',
    #     4: 'single chamber bipolar',
    #     5: 'dual chamber bipolar',
    # }

    # TODO: dictionaries for gender and race?

    def get_header_bytes(self):
        """Create the ISHNE header from the various instance variables.  The
        variable-length block is included, but the 10 'pre-header' bytes are
        not.

        This is the only function in the class that requires python3, for
        to_bytes().
        """
        header = bytearray()

        header += (self.var_block_size       ).to_bytes(4, sys.byteorder)
        header += (self.ecg_size             ).to_bytes(4, sys.byteorder)
        header += (self.var_block_offset     ).to_bytes(4, sys.byteorder)
        header += (self.ecg_block_offset     ).to_bytes(4, sys.byteorder)
        header += (self.file_version         ).to_bytes(2, sys.byteorder, signed=True)
        header += self.first_name          [:40].ljust(40, b'\x00')
        header += self.last_name           [:40].ljust(40, b'\x00')
        header += self.id                  [:20].ljust(20, b'\x00')
        header += (self.sex                  ).to_bytes(2, sys.byteorder)
        header += (self.race                 ).to_bytes(2, sys.byteorder)
        if self.birth_date:
            header += (self.birth_date.day   ).to_bytes(2, sys.byteorder)
            header += (self.birth_date.month ).to_bytes(2, sys.byteorder)
            header += (self.birth_date.year  ).to_bytes(2, sys.byteorder)
        else:
            header += (0                     ).to_bytes(6, sys.byteorder)  # TODO?: -9s
        if self.record_date:
            header += (self.record_date.day  ).to_bytes(2, sys.byteorder)
            header += (self.record_date.month).to_bytes(2, sys.byteorder)
            header += (self.record_date.year ).to_bytes(2, sys.byteorder)
        else:
            header += (0                     ).to_bytes(6, sys.byteorder)  # TODO?: -9s
        if self.file_date:
            header += (self.file_date.day    ).to_bytes(2, sys.byteorder)
            header += (self.file_date.month  ).to_bytes(2, sys.byteorder)
            header += (self.file_date.year   ).to_bytes(2, sys.byteorder)
        else:
            header += (0                     ).to_bytes(6, sys.byteorder)  # TODO?: -9s
        if self.start_time:
            header += (self.start_time.hour  ).to_bytes(2, sys.byteorder)
            header += (self.start_time.minute).to_bytes(2, sys.byteorder)
            header += (self.start_time.second).to_bytes(2, sys.byteorder)
        else:
            header += (0                     ).to_bytes(6, sys.byteorder)  # TODO?: -9s
        header += (self.nleads               ).to_bytes(2, sys.byteorder)
        for i in range(self.nleads):
            header += (self.lead[i].spec     ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(12-self.nleads):
            header += (-9                    ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(self.nleads):
            header += (self.lead[i].qual     ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(12-self.nleads):
            header += (-9                    ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(self.nleads):
            header += (self.lead[i].res      ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(12-self.nleads):
            header += (-9                    ).to_bytes(2, sys.byteorder, signed=True)
        header += (self.pm                   ).to_bytes(2, sys.byteorder, signed=True)
        header += self.recorder_type       [:40].ljust(40, b'\x00')
        header += (self.sr                   ).to_bytes(2, sys.byteorder)
        header += self.proprietary         [:80].ljust(80, b'\x00')
        header += self.copyright           [:80].ljust(80, b'\x00')
        header += self.reserved            [:88].ljust(88, b'\x00')
        if self.var_block_size > 0:
            header += self.var_block

        return bytes( header )

    def autofill_header(self):
        """Automatically update several header variables for consistency.  For example,
        ecg_size will be set to the current length of the data array, and
        var_block_size will be set to the current length of the variable block
        string.
        """
        self.magic_number = b'ISHNE1.0'
        try:
            self.var_block_size = len( self.var_block )
        except TypeError:
            self.var_block_size = 0
        try:
            self.ecg_size = len( self.lead[0].data )
            # it's not clear if we should report the total number of samples
            # for *one* lead, or for *all* leads.  we do the former.
        except TypeError:
            self.ecg_size = 0
        self.var_block_offset = 522
        self.ecg_block_offset = 522+self.var_block_size
        self.file_date = datetime.datetime.now().date()
        try:
            self.nleads = len( self.lead )
        except TypeError:
            self.nleads = 0
        # TODO?: checksum.  may break is_valid().

        # TODO: enforce proper values (or -9 or whatever) for all fields.  in
        # particular, lead spec, qual, and res need to be -9 for non-present
        # leads.  sex and race should be zeroed if they're invalid.  sr >
        # 0... we can't fix that without knowing it.  set pm to -9 if it's not a
        # value in pm_codes?

    def write_file(self, overwrite=False, convert_data=True):
        """This function will write the object to disk as an ISHNE Holter file.  You do
        *not* need to pre-set the following variables: magic_number, checksum,
        var_block_size, ecg_size, var_block_offset, ecg_block_offset, file_date, and
        nleads.  They will be updated automatically when this function is called.

        Keyword arguments:
        overwrite -- whether we should overwrite an existing file
        convert_data -- whether data needs to be converted back to int16 from float (mV)
        """
        data_counts = [len(lead.data) for lead in self.lead]
        assert len(set(data_counts)) == 1, "Every lead must have the same number of samples."

        if os.path.exists(self.filename):
            assert overwrite, "File with that name already exists."
            os.remove(self.filename)  # overwrite is enabled; rm the existing
                                      # file before we start (note: may fail if
                                      # it's a directory not a file)

        # Prepare known/computable values such as variable block offset:
        self.autofill_header()

        # Write file:
        with open(self.filename, 'ab') as f:
            header = self.get_header_bytes()
            # Preheader:
            f.write( b'ISHNE1.0' )
            f.write( self.compute_checksum(header_block=header) )
            # Header:
            f.write( header )
            # Data block:
            data = []
            for i in range(self.nleads):
                data += [ self.lead[i].data_int16(convert=convert_data) ]
            data = np.reshape( data, self.nleads*len(self.lead[0].data), 'F' )
            f.write( data )

class Lead:
    def __init__(self, spec, qual, res):
        """Store a lead's parameters (name, quality, and amplitude resolution).  Data
        (samples) from the lead will be loaded separately.

        Keyword arguments:
        spec -- numeric code from Table 1 of ISHNE Holter spec
        qual -- numeric code from Table 2 of ISHNE Holter spec
        res -- this lead's resolution in nV
        """
        self.spec = spec
        self.qual = qual
        self.res  = res
        self.data = None

    def save_data(self, data, convert=True):
        """Replace the data array for this lead with a new one, optionally converting
        from ISHNE format (int16 samples) to floats (units = mV).

        Keyword arguments:
        data -- 1d numpy array of samples for this lead
        convert -- whether sample values should be converted to mV
        """
        if convert:
            data = data.astype(float)
            data *= self.res/1e6
        self.data = data

    def data_int16(self, convert=True):
        """Returns data in the format for saving to disk.  Pointless to use if convert==False."""
        data = self.data
        if convert:
            data *= 1e6/self.res
            data = data.astype(np.int16)
        return data
        # TODO?: maybe do this the other way around, save data unaltered as
        # int16 and make converted available as e.g. self.data_mV().  That may
        # reduce possibility of rounding errors during conversions.

    def spec_str(self):
        """Return this lead's human-readable name (e.g. 'V1')."""
        lead_specs = {
            -9: 'absent', 0: 'unknown', 1: 'generic',
            2: 'X',    3: 'Y',    4: 'Z',
            5: 'I',    6: 'II',   7: 'III',
            8: 'aVR',  9: 'aVL', 10: 'aVF',
            11: 'V1', 12: 'V2',  13: 'V3',
            14: 'V4', 15: 'V5',  16: 'V6',
            17: 'ES', 18: 'AS',  19: 'AI'
        }
        return lead_specs[self.spec]

    def qual_str(self):
        """Return a description of this lead's quality (e.g. 'intermittent noise')."""
        lead_quals = {
            -9: 'absent',
            0: 'unknown',
            1: 'good',
            2: 'intermittent noise',
            3: 'frequent noise',
            4: 'intermittent disconnect',
            5: 'frequent disconnect'
        }
        return lead_quals[self.qual]

################################################################################
