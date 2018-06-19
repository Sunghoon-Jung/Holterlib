"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

# default values for fields that may be set/edited by the user
header_field_defaults = {
    'file_version':  -9,
    'first_name':    '',
    'last_name':     '',
    'id':            '',
    'sex':           0,
    'race':          0,
    'birth_date':    None,
    'pm':            -9,
    'recorder_type': '',  # TODO?: 'unknown'
    'proprietary':   '',
    'copyright':     '',
    'reserved':      '',
    'var_block':     ''
}

# numeric codes from Table 1 of ISHNE Holter spec
lead_specs = {
    -9: 'absent', 0: 'unknown', 1: 'generic',
    2: 'X',    3: 'Y',    4: 'Z',
    5: 'I',    6: 'II',   7: 'III',
    8: 'aVR',  9: 'aVL', 10: 'aVF',
    11: 'V1', 12: 'V2',  13: 'V3',
    14: 'V4', 15: 'V5',  16: 'V6',
    17: 'ES', 18: 'AS',  19: 'AI'
}

# numeric codes from Table 2 of ISHNE Holter spec
lead_qualities = {
    -9: 'absent',
    0: 'unknown',
    1: 'good',
    2: 'intermittent noise',
    3: 'frequent noise',
    4: 'intermittent disconnect',
    5: 'frequent disconnect'
}

# type of pacemaker
pm_codes = {
    0: 'none',  # i.e. no PM installed.  so -9 should be used for unknown.
    1: 'unknown type',
    2: 'single chamber unipolar',
    3: 'dual chamber unipolar',
    4: 'single chamber bipolar',
    5: 'dual chamber bipolar',
}

gender_codes = {
    0: None,  # unknown
    1: 'M',
    2: 'F'
}

# race codes.  other values (e.g. 4+) may also be used, but weren't in the initial spec
race_codes = {
    0: None,  # unknown
    1: 'caucasian',
    2: 'black',
    3: 'oriental',
}
