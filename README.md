
# WCA Regulations Compiler

This is a tool to check, build, compare WCA Regulations and Guidelines and its translations.

## Install from PyPi

Just run `pip install wrc`.

## External dependencies

If you want to build the pdf versions, you need the **patched qt** version of [wkhtmltopdf](http://wkhtmltopdf.org/) in your `$PATH`.
These stable standalone binaries are available [here](http://wkhtmltopdf.org/downloads.html) for several platforms.

For CJK translations you also need to install some packages providing CJK fonts. The official build uses "UnBatang" for Korean (package `fonts-unfonts-core` or alike), "WenQuanYi Micro Hei" for Chinese (package `fonts-wqy-microhei` or alike), and "IPAX0208PGothic" for Japanese (package `fonts-ipafont` or alike).

## Run the thing

Here are some sample invocations:

- To check the Regulations and Guidelines:
`wrc path/to/wca-regulations --target=check`
- To build the html to the `build` directory:
`wrc path/to/wca-regulations --target=html --output=build`
- When building translation it's necessary to provide the language (to choose the appropriate font/pdf names):
`wrc path/to/wca-regulations-translations/french --language=french --target=pdf --output=build`
- Check that a translation matches exactly the original rules:
`wrc path/to/wca-regulations-translations/french --diff=path/to/wca-regulations`

You can also take a look at the travis [script](https://github.com/thewca/wca-regulations-translations/blob/master/travis.sh) used in the translations repository.


## Running from the sources

Note: the whole project is written using python 2.7, if something goes wrong it's likely because your `python` command defaults to python 3.

The compiler is built on top of python lex/yacc implementation `ply`, so you probably need to run `pip install ply` to install it.
When this is done, you can use `python -m wrc.wrc` from the repository's root instead of `wrc`.
If you want to use `wrc-states` from the source, an easy way to do this is to run `python -c "from wrc.wrc import states; states()"`

## Deploying to PyPi

(section for maintainers in PyPi)

- Bump the version number in `wrc/version.py`
- Clean the `dist` and `wrc.egg_info` directories
- `python2 setup.py egg_info`
- `python2 setup.py sdist bdist_wheel`
- `twine upload dist/*`
