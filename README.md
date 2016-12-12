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

    # Delete leads other than V2:
    leadspecs = [ x.get_leadspec(i) for i in range(x.nleads) ]
    keep = leadspecs.index('V2')
    x.data = [ x.data[keep] ]

    # Write back to disk:
    x.write_file(overwrite=True)

### Who do I talk to? ###

* Alex Page, alex.page@rochester.edu