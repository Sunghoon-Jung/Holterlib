#!/usr/bin/env python3

"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

import os
import numpy as np
import datetime
import sys
from PyCRC.CRCCCITT import CRCCCITT
from ecgplotter import Lead

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

################################## Constants: ##################################

header_fields = ['file_version', 'first_name', 'last_name', 'id', 'sex', 'race',
                 'birth_date', 'record_date', 'file_date', 'start_time',
                 'nleads', 'pm', 'recorder_type', 'sr', 'proprietary',
                 'copyright', 'reserved']

lead_specs = {
    -9: 'absent', 0: 'unknown', 1: 'generic',
    2: 'X',    3: 'Y',    4: 'Z',
    5: 'I',    6: 'II',   7: 'III',
    8: 'aVR',  9: 'aVL', 10: 'aVF',
    11: 'V1', 12: 'V2',  13: 'V3',
    14: 'V4', 15: 'V5',  16: 'V6',
    17: 'ES', 18: 'AS',  19: 'AI'
}

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
                    setattr(self, field, None)
            # TODO: initialize any remaining fields with default values

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
        # TODO: handle NULLs and fix lead_specs
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

        
class Holter:
    """header is a Header object.  leads is a list of Lead objects.  filename is
    where we will read from if those aren't specified, or where we plan to write
    to later.  annfile indicates that this Holter is storing annotations, not
    voltage measurements.  If load_data is False and we need to load the file
    from disk, we will only load the header for now.
    """
    def __init__(self, filename=None, header=None, leads=None, check_valid=True, annfile=False, load_data=False):
        self.filename = filename
        self.is_annfile = annfile
        # self.beat_anns = []
        if header==None and leads==None and os.path.exists(filename):
            # TODO: what if filename was specified but the file didn't exist?
            # how do we know they didn't want to read it?  if they did, we
            # should return an error.
            self.header = Header(filename=filename)
            if load_data:
                if annfile:
                    pass
                    # TODO: load anns
                else:
                    self.load_data()
            else:
                print( "Loaded header successfully.  Remember to run load_data() if you need the data too." )
        else:
            if leads  != None: self.lead = leads
            else:              self.lead = []
            if header != None: self.header = header
            else:              self.header = Header()
        # if check_valid and not self.is_valid():
        #     raise Warning( "File appears to be invalid or corrupt. (%s)" % filename )
        # # TODO: modify/disable parts of whole class appropriately when is_annfile is True.

    def load_data(self):
        """This may take some time and memory, so we don't do it until we're asked.  The
        'lead' variable is a list of Lead objects where lead[i].ampl is the data
        for lead number i.  Existing Leads will be deleted when this function is called.
        """
        # Get the data:
        with open(self.filename, 'rb') as f:
            f.seek(self.ecg_block_offset, os.SEEK_SET)
            data = np.fromfile(f, dtype=np.int16)
        # Convert it to a 2D array, cropping the end if necessary:
        nleads = self.nleads
        data = np.reshape( data[:int(len(data)/nleads)*nleads],
                                (nleads, int(len(data)/nleads)),
                                order='F' )
        # Save each row (lead), converting measurements from ADC units to mV in the process:
        self.lead = []
        for i in range(nleads):
            self.lead.append(
                Lead(ampl       = data[i],
                     start_time = datetime.datetime.combine(self.header.record_date,
                                                            self.header.start_time),
                     umV        = 1e6/self.ampl_res[i],
                     sr         = TODO,
                     name       = self.lead_spec[i])
            )
        # TODO: store lead_quality in Lead somehow.  (extend the class to add it?)

    # def __str__(self):
    #     result = ''
    #     for key in vars(self):
    #         if key == 'lead':
    #             result += 'leads: ' + str([str(l) for l in self.lead]) + '\n'
    #         elif key == 'beat_anns':
    #             result += 'beat_anns: %d beat annotations\n' % len(self.beat_anns)
    #         else:
    #             result += key + ': ' + str(vars(self)[key]) + '\n'
    #     return result.rstrip()
    #     # TODO: convert gender, race, pacemaker to readable form.  maybe do
    #     # ckstr(checksum) too.  units on values?


    # def load_ann(self, annfile=None):
    #     """Load beat annotations in accordance with
    #     http://thew-project.org/papers/ishneAnn.pdf.  The path to the annotation
    #     file can be specified manually, otherwise we will look for a file with a
    #     .ann extension alongside the original ECG.  self.beat_anns is indexed as
    #     beat_anns[beat number]['key']."""
    #     if annfile==None:
    #         annfile = os.path.splitext(self.filename)[0]+'.ann'
    #     annheader = Holter(annfile, annfile=True)  # note, var_block_offset may be wrong in .ann files
    #     filesize = os.path.getsize(annfile)
    #     headersize = 522 + annheader.var_block_size + 4
    #     self.beat_anns = []
    #     with open(annfile, 'rb') as f:
    #         f.seek(headersize-4, os.SEEK_SET)
    #         first_sample = np.fromfile(f, dtype=np.uint32, count=1)[0]
    #         current_sample = first_sample
    #         timeout = False  # was there a gap in the annotations?
    #         for beat in range( int((filesize - headersize) / 4) ):
    #             # note, the beat at first_sample isn't annotated.  so the first beat
    #             # in beat_anns is actually the second beat of the recording.
    #             ann      = chr(np.fromfile(f, dtype=np.uint8, count=1)[0])
    #             internal = chr(np.fromfile(f, dtype=np.uint8, count=1)[0])
    #             toc      =     np.fromfile(f, dtype=np.int16, count=1)[0]
    #             current_sample += toc
    #             if ann == '!':
    #                 timeout = True  # there was a few minutes gap in the anns; don't
    #                                 # know how to line them up to rest of recording
    #             self.beat_anns.append( {'ann': ann, 'internal': internal, 'toc': toc} )
    #             if not timeout:
    #                 self.beat_anns[-1]['samp_num'] = current_sample

    # def compute_checksum(self, header_block=None):
    #     """Compute checksum of header block.  If header_block is None, it operates on
    #     the file on disk (pointed to by self.filename).

    #     Keyword arguments:
    #     header_block -- a bytes object containing the ISHNE header (typically bytes 10-522 of the file)
    #     """
    #     if header_block == None:
    #         with open(self.filename, 'rb') as f:
    #             f.seek(10, os.SEEK_SET)
    #             header_block = np.fromfile(f, dtype=np.uint8, count=self.ecg_block_offset-10)
    #             header_block = header_block.tostring()  # to make it a bytes object
    #     return np.uint16( CRCCCITT(version='FFFF').calculate(header_block) )
    #     # Another method to do the calculation:
    #     #   from crccheck.crc import Crc16CcittFalse
    #     #   Crc16CcittFalse.calc( header )

    # def is_valid(self, verify_checksum=True):
    #     """Check for obvious problems with the file: wrong file signature, bad checksum,
    #     or invalid values for file or header size.
    #     """
    #     # Check magic number:
    #     if self.is_annfile: expected_magic_number = b'ANN  1.0'
    #     else:               expected_magic_number = b'ISHNE1.0'
    #     if self.magic_number != expected_magic_number:
    #         return False
    #     # Var block should always start at 522:
    #     if self.var_block_offset != 522:
    #         return False
    #     # Check file size.  We have no way to predict this for annotations,
    #     # because it depends on heart rate and annotation quality:
    #     if not self.is_annfile:
    #         filesize = os.path.getsize(self.filename)
    #         expected = 522 + self.var_block_size + 2*self.ecg_size
    #         if filesize!=expected:
    #             # ecg_size may have been reported as samples per lead instead of
    #             # total number of samples
    #             expected += 2*self.ecg_size*(self.nleads-1)
    #             if filesize!=expected:
    #                 return False
    #     # Verify CRC:
    #     if verify_checksum and (self.checksum != self.compute_checksum()):
    #         return False
    #     # TODO?: check SR > 0
    #     return True  # didn't find any problems above
    #     # TODO?: make this function work with in-memory Holter, i.e. not just
    #     # one that we loaded from disk.

    # def get_length(self):
    #     """Return the duration of the Holter as a timedelta object.  If data has already
    #     been loaded, duration will be computed as the length of the first lead
    #     in memory.  Otherwise, it will be computed from the size of the original
    #     file on disk.
    #     """
    #     try:
    #         duration = datetime.timedelta(seconds = 1.0 * len(self.lead[0].data) / self.sr)
    #     except TypeError:  # self.lead[0] probably doesn't exist
    #         try:
    #             filesize = os.path.getsize(self.filename)
    #             duration = datetime.timedelta(seconds =
    #                 1.0*(filesize - 522 - self.var_block_size) / 2 / self.nleads / self.sr
    #             )
    #         except OSError:  # probably bad path to original file
    #             duration = None
    #     return duration


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

################################################################################