import setuptools

setuptools.setup(
    name='ishneholterlib',
    version='2017.04.11',
    description='A library to work with ISHNE-formatted Holter ECG files',
    # long_description=long_description,
    # long_description_content_type='text/markdown',
    url='https://bitbucket.org/atpage/ishneholterlib',
    author='Alex Page',
    author_email='alex.page@rochester.edu',
    license='MIT',
    # packages=['ishneholterlib'],
    packages=setuptools.find_packages(),
    install_requires=['numpy', 'PyCRC'],
    keywords='ISHNE Holter ECG EKG',
    zip_safe=False,
    # classifiers=(
    #     'Programming Language :: Python :: 3',
    # ),
)
