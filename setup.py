from setuptools import setup, find_packages

setup(name='wrc',
      version='1.0.0a1',
      description='Tool to build and perform checks on WCA Regulations and Guidelines',
      url='http://github.com/viroulep/wca-regulations-compiler',
      author='Philippe Virouleau',
      author_email='philippe.44@gmail.com',
      license='GPLv3',
      packages=find_packages(),
      entry_points={
          'console_scripts': ['wrc=wrc.wrc:run'],
      },
      zip_safe=False)
