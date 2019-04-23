# ISHNE Holter Library for Python #

A library to work with ISHNE-formatted Holter ECG files

### Prerequisites ###

* Python3 (basically only needed for writing files; otherwise you can try Python2)
* numpy 
* PyCRC

### Installation ###

    $ pip3 install ishneholterlib

### Example ###

    from ishneholterlib import Holter
    
    # Load a file from disk:
    x = Holter('some_holter.ecg')
    x.load_data()
    
    # Delete leads other than V2:
    x.lead = [l for l in x.lead if str(l)=='V2']
    
    # Write back to disk:
    x.write_file(overwrite=True)

### Description of instance variables ###

In the example above, `x` contains the following variables:

* `filename`: filename specified when `x` was instantiated
* `lead`: list of Lead objects, each containing the following:
    * `spec`: lead type, e.g. 11='V1'
    * `qual`: lead quality, e.g. 3='frequent noise'
    * `res`: lead resolution in nV
    * `data`: 1d array of samples for this lead, in mV
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
* `pm`: pacemaker code, e.g. 2='single chamber unipolar'
* `recorder_type`: analog or digital
* `sr`: sample rate in Hz
* Miscellaneous text blocks: `proprietary`, `copyright`, and `reserved`
* `var_block`: variable-length text block, not always present

Everything except `data` is loaded when `x` is instantiated.  `load_data()` is then called to populate `data` for each lead.  Finally, to get at the original signal, you can access:

    x.lead[0].data  # lead 1 signal
    x.lead[1].data  # lead 2 signal
    # ... etc.

See http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf to decode the values that use a dictionary, such as the gender, race, and pacemaker fields.  `spec_str()` and `qual_str()` are provided to decode the name and quality of each lead.

### Who do I talk to? ###

* Alex Page, alex.page@rochester.edu