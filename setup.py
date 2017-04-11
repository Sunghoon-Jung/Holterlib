from setuptools import setup

setup( name='ishneholterlib',
       version='2017.01.18',
       description='A library to work with ISHNE-formatted Holter ECG files',
       url='https://bitbucket.org/atpage/ishneholterlib',
       author='Alex Page',
       author_email='alex.page@rochester.edu',
       license='MIT',
       packages=['ishneholterlib'],
       install_requires=['numpy', 'PyCRC'],
       keywords='ISHNE Holter ECG EKG',
       zip_safe=False )
