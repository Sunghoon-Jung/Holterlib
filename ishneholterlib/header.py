"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

import os
import numpy as np
import sys
from .helpers import get_val, get_short_int, get_long_int, get_datetime
from .constants import header_field_defaults

class Header:
    def __init__(self, filename=None, **kwargs):
        """Create a new ISHNE Holter Header, either from disk or from provided
        arguments.  If filename is set, all other args will be ignored.  Default
        values (e.g. None or '') will be used for any args not provided.

        Keyword arguments:
        filename -- file to load the header from
        file_version -- integer
        first_name -- string
        last_name -- string
        id -- string
        sex -- integer key for constants.gender_codes
        race -- integer key for constants.race_codes
        birth_date -- datetime.date
        record_date -- datetime.date
        file_date -- datetime.date
        start_time -- datetime.time
        pm -- integer key for constants.pm_codes
        recorder_type -- string (e.g. 'analog' or 'digital')
        proprietary -- string
        copyright -- string
        reserved -- string
        var_block -- string
        """
        self.filename = filename
        if filename != None:
            # load fields from disk
            self.load_header()
        else:
            # create new header, not from disk
            for field in header_field_defaults:
                if field in kwargs:
                    setattr(self, field, kwargs[field])  # user specified value
                else:
                    setattr(self, field, header_field_defaults[field])  # default value like None

    def load_header(self):
        filename = self.filename
        if os.path.getsize(filename) < 522:
            raise FileNotFoundError("File is too small to be an ISHNE Holter.")
        # "Pre"-header:
        self.magic_number = get_val(filename, 0, 'a8')
        self.checksum = get_val(filename, 8, np.uint16)
        # Fixed-size part of header:
        var_block_size     =   get_long_int(filename,  10)
        self.ecg_size      =   get_long_int(filename,  14)  # in number of samples
        var_block_offset   =   get_long_int(filename,  18)  # start of variable-length block
        ecg_block_offset   =   get_long_int(filename,  22)  # start of ECG samples
        self.file_version  =  get_short_int(filename,  26)
        self.first_name    =        get_val(filename,  28, 'a40').split(b'\x00')[0]
        self.last_name     =        get_val(filename,  68, 'a40').split(b'\x00')[0]
        self.id            =        get_val(filename, 108, 'a20').split(b'\x00')[0]
        self.sex           =  get_short_int(filename, 128)  # 1=male, 2=female
        self.race          =  get_short_int(filename, 130)  # 1=white, 2=black, 3=oriental
        self.birth_date    =   get_datetime(filename, 132)
        self.record_date   =   get_datetime(filename, 138)  # recording date
        self.file_date     =   get_datetime(filename, 144)  # date of creation of output file
        self.start_time    =   get_datetime(filename, 150, time=True)  # start time of Holter
        nleads             =  get_short_int(filename, 156)
        self.lead_spec     = [get_short_int(filename, 158+i*2) for i in range(12)]
        self.lead_quality  = [get_short_int(filename, 182+i*2) for i in range(12)]
        self.ampl_res      = [get_short_int(filename, 206+i*2) for i in range(12)]  # lead resolution in nV
        # TODO: don't store spec/quality/res in header; they will be stored in Leads
        self.pm            =  get_short_int(filename, 230)  # pacemaker
        self.recorder_type =        get_val(filename, 232, 'a40').split(b'\x00')[0]  # analog or digital
        sr                 =  get_short_int(filename, 272)  # sample rate in Hz
        self.proprietary   =        get_val(filename, 274, 'a80').split(b'\x00')[0]
        self.copyright     =        get_val(filename, 354, 'a80').split(b'\x00')[0]
        self.reserved      =        get_val(filename, 434, 'a88').split(b'\x00')[0]
        # TODO?: read all the above with one open()
        if var_block_offset != 522 or \
           ecg_block_offset != 522+var_block_size:
            raise ValueError("File header contains an invalid value.")
        # Variable-length part of header:
        if var_block_size > 0:
            self.var_block = get_val(filename, 522, 'a'+str(var_block_size)).split(b'\x00')[0]
        else:
            self.var_block = header_field_defaults['var_block']

    def get_header_bytes(self, leads):
        """Create the (byte array) ISHNE header from the various instance variables.
        The variable-length block is included, but the 10 'pre-header' bytes are
        not.

        Note: We use the convention that ecg_size is the number of samples in
        ONE lead.  Some software may instead expect ecg_size to be the total
        number of samples including ALL leads.  The specification document is
        not clear which convention should be used.

        Keyword arguments:
        leads -- list of Lead objects associated with this Header
        """
        # TODO?: make this a function of (header,leads) and put somewhere else

        if len(set([l.sr        for l in leads])) != 1 or \
           len(set([l.time[0]   for l in leads])) != 1 or \
           len(set([len(l.ampl) for l in leads])) != 1:
            raise ValueError("Leads must be same length and sample rate, and start at the same time.")
        # TODO: leads must store umV, name, quality
        
        header = bytearray()
        header += (len(self.var_block)       ).to_bytes(4, sys.byteorder)
        header += (len(leads[0].ampl)        ).to_bytes(4, sys.byteorder)
        header += (522                       ).to_bytes(4, sys.byteorder)
        header += (522+len(self.var_block)   ).to_bytes(4, sys.byteorder)
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
        header += (len(leads)                ).to_bytes(2, sys.byteorder)

        
        # TODO: from Leads, will need reverse lookup:
        for l in leads:
            header += (l.name_TODO_TO_KEY    ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(12-len(leads)):
            header += (-9                    ).to_bytes(2, sys.byteorder, signed=True)

        # TODO: from Leads, will need reverse lookup:
        for l in leads:
            header += (self.lead[i].qual     ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(12-len(leads)):
            header += (-9                    ).to_bytes(2, sys.byteorder, signed=True)
            
        # TODO: from Leads, will need reverse lookup:
        for l in leads:
            header += (self.lead[i].res      ).to_bytes(2, sys.byteorder, signed=True)
        for i in range(12-len(leads)):
            header += (-9                    ).to_bytes(2, sys.byteorder, signed=True)

            
        header += (self.pm                   ).to_bytes(2, sys.byteorder, signed=True)
        header += self.recorder_type       [:40].ljust(40, b'\x00')
        header += (leads[0].sr               ).to_bytes(2, sys.byteorder)
        header += self.proprietary         [:80].ljust(80, b'\x00')
        header += self.copyright           [:80].ljust(80, b'\x00')
        header += self.reserved            [:88].ljust(88, b'\x00')
        if len(self.var_block) > 0:
            header += self.var_block
        return bytes( header )
