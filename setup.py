from setuptools import setup, find_packages
from wrc.version import __version__

setup(name='wrc',
      version=__version__,
      description='Tool to build and perform checks on WCA Regulations and Guidelines',
      url='https://github.com/thewca/wca-regulations-compiler',
      author='Philippe Virouleau',
      author_email='philippe.44@gmail.com',
      license='GPLv3',
      packages=find_packages(),
      install_requires=['ply>=3.7', 'unidecode'],
      package_data={
          'wrc': ['data/*'],
      },
      entry_points={
          'console_scripts': ['wrc=wrc.wrc:run', 'wrc-languages=wrc.wrc:languages', 'wrc-states=wrc.wrc:states'],
      },
      zip_safe=False)
