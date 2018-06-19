#!/usr/bin/env python3

"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

import os
import numpy as np
import datetime
import sys
from PyCRC.CRCCCITT import CRCCCITT
from ecgplotter import Lead
from .constants import lead_qualities

################################### Classes: ###################################

class Holter:
    def __init__(self, filename=None, header=None, leads=None, check_valid=True, annfile=False, load_data=False):
        """header is a Header object.  leads is a list of Lead objects.  filename is
        where we will read from if those aren't specified, or where we plan to
        write to later.  annfile indicates that this Holter is storing
        annotations, not voltage measurements.  If load_data is False and we
        need to load the file from disk, we will only load the header for now.
        """
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
        # # Create array of Leads (where lead specs and data will be stored):
        # self.lead = [None for _ in range(self.nleads)]
        # for i in range(self.nleads):
        #     self.lead[i] = Lead(lead_spec[i], lead_quality[i], ampl_res[i])
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
                     umV        = 1e6/self.header.ampl_res[i],  # TODO: ensure float
                     sr         = self.header.sr,
                     name       = self.header.lead_spec[i],
                     notes      = {
                         'quality': lead_qualities[self.header.lead_quality[i]],  # TODO
                     },
                )
            )
        # TODO: store lead_quality in Lead somehow.  (extend the class to add it?)
        
    def get_header_bytes(self):
        """Create the (byte array) ISHNE header from the various instance variables.
        The variable-length block is included, but the 10 'pre-header' bytes are
        not.
    
        Note: We use the convention that ecg_size is the number of samples in ONE
        lead.  Some software may instead expect ecg_size to be the total number of
        samples including ALL leads.  The specification document is not clear which
        convention should be used.
    
        Keyword arguments:
        header -- Header object
        leads  -- list of Lead objects associated with the Header
        """
        header, leads = self.header, self.leads
        if len(set([l.sr        for l in leads])) != 1 or \
           len(set([l.time[0]   for l in leads])) != 1 or \
           len(set([len(l.ampl) for l in leads])) != 1:
            raise ValueError("Leads must be same length and sample rate, and start at the same time.")
        header_bytes = bytearray()
        header_bytes += (len(header.var_block)            ).to_bytes(4, sys.byteorder)
        header_bytes += (len(leads[0].ampl)               ).to_bytes(4, sys.byteorder)
        header_bytes += (522                              ).to_bytes(4, sys.byteorder)
        header_bytes += (522+len(header.var_block)        ).to_bytes(4, sys.byteorder)
        header_bytes += (header.file_version              ).to_bytes(2, sys.byteorder, signed=True)
        header_bytes += header.first_name               [:40].ljust(40, b'\x00')
        header_bytes += header.last_name                [:40].ljust(40, b'\x00')
        header_bytes += header.id                       [:20].ljust(20, b'\x00')
        header_bytes += (header.sex                       ).to_bytes(2, sys.byteorder)
        header_bytes += (header.race                      ).to_bytes(2, sys.byteorder)
        header_bytes += bytes_from_datetime(header.birth_date)      #6
        header_bytes += bytes_from_datetime(leads[0].time[0].date())#6
        header_bytes += bytes_from_datetime(header.file_date)       #6
        header_bytes += bytes_from_datetime(leads[0].time[0].time())#6
        header_bytes += (len(leads)                       ).to_bytes(2, sys.byteorder)
        header_bytes += bytes_from_lead_names(leads)               #24
        header_bytes += bytes_from_lead_qualities(leads)           #24
        header_bytes += bytes_from_lead_resolutions(leads)         #24
        header_bytes += (header.pm                        ).to_bytes(2, sys.byteorder, signed=True)
        header_bytes += header.recorder_type            [:40].ljust(40, b'\x00')
        header_bytes += (leads[0].sr                      ).to_bytes(2, sys.byteorder)
        header_bytes += header.proprietary              [:80].ljust(80, b'\x00')
        header_bytes += header.copyright                [:80].ljust(80, b'\x00')
        header_bytes += header.reserved                 [:88].ljust(88, b'\x00')
        if len(header.var_block) > 0:
            header_bytes += header.var_block
        return bytes( header_bytes )

    def compute_checksum(self):
        """Compute checksum of header block (typically bytes 10-522 of the file)."""
        header_block = self.get_header_bytes()  # .tostring()
        return np.uint16( CRCCCITT(version='FFFF').calculate(header_block) )
        # Another method to do the calculation:
        #   from crccheck.crc import Crc16CcittFalse
        #   Crc16CcittFalse.calc( header_block )

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
        # TODO: should be renamed to something like update_header_fields().
        # (possibly run some of it automatically when Leads change?)
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

    def data_int16(self, convert=True):
        """Returns data in the format for saving to disk.  Pointless to use if convert==False."""
        data = self.data.copy()
        if convert:
            data *= 1e6/self.res
            data = data.astype(np.int16)
        return data
        
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
