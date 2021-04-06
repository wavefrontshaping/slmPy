import setuptools
# from packagename.version import Version

setuptools.setup(name='slmpy',
                 version='0.222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222.0',
                 description='Display images on a spatial light modulators.',
                 long_description=open('README.md').read().strip(),
                 author="Sebastien M. Popoff",
                 author_email='sebastien.popoff@espci.psl.eu',
                 url='https://github.com/wavefrontshaping/slmPy',
                 py_modules=['slmpy.slmpy'],
                 install_requires=['numpy', 'wxPython'],
                 license='MIT License',
                 zip_safe=False,
                 keywords='numpy, python3, slm, wavefront shaping, display',
                 classifiers=[''])
