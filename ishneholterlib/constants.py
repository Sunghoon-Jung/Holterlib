#!/usr/bin/env python3

"""Reference: http://thew-project.org/papers/Badilini.ISHNE.Holter.Standard.pdf"""

################################## Constants: ##################################

# fields that may be set/edited by the user
header_fields = ['file_version', 'first_name', 'last_name', 'id', 'sex', 'race',
                 'birth_date', 'record_date', 'file_date', 'start_time',
                 'nleads', 'pm', 'recorder_type', 'sr', 'proprietary',
                 'copyright', 'reserved']

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

################################################################################
