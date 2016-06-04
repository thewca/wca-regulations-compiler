from setuptools import setup, find_packages

setup(name='wrc',
      version='1.0.1',
      description='Tool to build and perform checks on WCA Regulations and Guidelines',
      url='http://github.com/viroulep/wca-regulations-compiler',
      author='Philippe Virouleau',
      author_email='philippe.44@gmail.com',
      license='GPLv3',
      packages=find_packages(),
      install_requires=['ply>=3.7'],
      package_data={
          'wrc': ['data/*'],
      },
      entry_points={
          'console_scripts': ['wrc=wrc.wrc:run', 'wrc-languages=wrc.wrc:languages'],
      },
      zip_safe=False)
