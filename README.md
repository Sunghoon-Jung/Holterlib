# ISHNE Holter Library for Python #

This library is useful for working with ISHNE-formatted Holter ECG files in Python.

### Prerequisites ###

* Python3 (basically only needed for writing files; otherwise you can try Python2)
* numpy 
* PyCRC

### Installation ###

Add the library's location to your Python path.  In Linux:

    $ export PYTHONPATH=$PYTHONPATH:/path/to/ISHNEHolterLib

In Windows: append the library location to the PYTHONPATH variable in System Properties -> Advanced -> Environment Variables.

### Example ###

    from ISHNEHolterLib import Holter

    # Load a file from disk:
    x = Holter('some_holter.ecg')
    x.load_data()

    # Delete data from leads other than V2:
    leadspecs = [ x.get_leadspec(i) for i in range(x.nleads) ]
    keep = leadspecs.index('V2')
    x.data = [ x.data[keep] ]

    # Since V2 is now the first lead, copy its specs to that lead:
    x.lead_spec[0] = x.lead_spec[keep]
    x.lead_quality[0] = x.lead_quality[keep]
    x.ampl_res[0] = x.ampl_res[keep]

    # Write back to disk:
    x.write_file(overwrite=True)

### Description of instance variables ###

In the example above, `x` contains the following variables:

* `filename`: filename specified when `x` was instantiated
* `data`: m by n array of ECG samples.  m=lead, n=sample number.  units are mV.
* `file_version`
* `first_name` and `last_name`
* `id`
* `sex`: 1=male, 2=female
* `race`: 1=white, 2=black, 3=oriental
* `birth_date` as a datetime.date object
* `record_date` as a datetime.date object
* `file_date` as a datetime.date object
* `start_time` as a datetime.time object
* `nleads`: number of leads
* `lead_spec`: array of lead types, e.g. 11='V1'
* `lead_quality`: array of lead qualities, e.g. 3='frequent noise'
* `ampl_res`: array of lead resolutions in nV
* `pm`: pacemaker code, e.g. 2='single chamber unipolar'
* `recorder_type`: analog or digital
* `sr`: sample rate in Hz
* Miscellaneous text blocks: `proprietary`, `copyright`, and `reserved`
* `var_block`: variable-length text block, not always present

Everything except `data` is loaded when `x` is instantiated.  `load_data()` is then called to populate `data`.

See http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf to decode the values that use a dictionary.  `get_leadspec()` can decode the ones in `lead_spec`.

### Who do I talk to? ###

* Alex Page, alex.page@rochester.edu