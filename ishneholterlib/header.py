#!/usr/bin/env python3

"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

import os
import numpy as np
import datetime
import sys

################################### Classes: ###################################

class Header:
    def __init__(self, filename=None, **kwargs):
        """kwargs are the values for file_version, first_name, last_name,
        id, sex, race, birth_date, record_date, file_date, start_time, nleads,
        pm, recorder_type, sr, proprietary, copyright, and reserved.  They will
        be ignored if a filename is specified, because the fields will be loaded
        from the file instead.
        """
        self.filename = filename
        if filename != None:
            # load fields from disk
            self.load_header()
        else:
            # create new header, not from disk
            for field in header_fields:
                if field in kwargs:
                    setattr(self, field, kwargs[field])
                else:
                    setattr(self, field, None)  # TODO?: different defaults than None

    def load_header(self):
        filename = self.filename
        if os.path.getsize(filename) < 522:
            raise FileNotFoundError("File is too small to be an ISHNE Holter.")
        self.magic_number = get_val(filename, 0, 'a8')
        self.checksum = get_val(filename, 8, np.uint16)
        # Fixed-size part of header:
        self.var_block_size   =   get_long_int(filename,  10)
        self.ecg_size         =   get_long_int(filename,  14)  # in number of samples
        self.var_block_offset =   get_long_int(filename,  18)  # start of variable-length block
        self.ecg_block_offset =   get_long_int(filename,  22)  # start of ECG samples
        self.file_version     =  get_short_int(filename,  26)
        self.first_name       =        get_val(filename,  28, 'a40').split(b'\x00')[0]
        self.last_name        =        get_val(filename,  68, 'a40').split(b'\x00')[0]
        self.id               =        get_val(filename, 108, 'a20').split(b'\x00')[0]
        self.sex              =  get_short_int(filename, 128)  # 1=male, 2=female
        self.race             =  get_short_int(filename, 130)  # 1=white, 2=black, 3=oriental
        self.birth_date       =   get_datetime(filename, 132)
        self.record_date      =   get_datetime(filename, 138)  # recording date
        self.file_date        =   get_datetime(filename, 144)  # date of creation of output file
        self.start_time       =   get_datetime(filename, 150, time=True)  # start time of Holter
        self.nleads           =  get_short_int(filename, 156)
        self.lead_spec        = [get_short_int(filename, 158+i*2) for i in range(12)]
        self.lead_spec        = [lead_specs[s] for s in self.lead_spec]
        self.lead_quality     = [get_short_int(filename, 182+i*2) for i in range(12)]
        self.lead_quality     = [lead_qualities[s] for s in self.lead_quality]
        self.ampl_res         = [get_short_int(filename, 206+i*2) for i in range(12)]  # lead resolution in nV
        self.pm               =  get_short_int(filename, 230)  # pacemaker
        self.recorder_type    =        get_val(filename, 232, 'a40').split(b'\x00')[0]  # analog or digital
        self.sr               =  get_short_int(filename, 272)  # sample rate in Hz
        self.proprietary      =        get_val(filename, 274, 'a80').split(b'\x00')[0]
        self.copyright        =        get_val(filename, 354, 'a80').split(b'\x00')[0]
        self.reserved         =        get_val(filename, 434, 'a88').split(b'\x00')[0]
        # TODO?: read all the above with one open()
        # Variable-length part of header:
        if self.var_block_size > 0:
            self.var_block = get_val(filename, 522, 'a'+str(self.var_block_size)).split(b'\x00')[0]
        else:
            self.var_block = None
        # # Create array of Leads (where lead specs and data will be stored):
        # self.lead = [None for _ in range(self.nleads)]
        # for i in range(self.nleads):
        #     self.lead[i] = Lead(lead_spec[i], lead_quality[i], ampl_res[i])

    def get_header_bytes(self):
        """Create the ISHNE header from the various instance variables.  The
        variable-length block is included, but the 10 'pre-header' bytes are
        not.
        """
        # TODO: handle NULLs and fix lead specs+qualities
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

################################################################################
