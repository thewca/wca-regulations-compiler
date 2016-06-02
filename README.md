
# WCA Regulations Compiler

Right now it's an attempt to build a more robust tool to check, build, compare WCA Regulations and Guidelines and its translations.

## Install from PyPi

Just run `pip install wrc`.

## Run the thing

Here are some sample invocations:

- To check the Regulations and Guidelines:
`wrc path/to/wca-regulations --target=check`
- To build the html to the `build` directory:
`wrc path/to/wca-regulations --target=html --output=build`
- When building translation it's necessary to provide the language (eg: for Latex stuff):
`wrc path/to/wca-regulations-translations/french --language=french --target=pdf --output=build`
- Check that a translation matches exactly the original rules:
`wrc path/to/wca-regulations-translations/french --diff=path/to/wca-regulations`


## Running from the sources

The compiler is built on top of python lex/yacc implementation `ply`, so you probably need to run `pip install ply` to install it.
When this is done, you can use `python -m wrc.wrc` from the repository's root instead of `wrc`.
