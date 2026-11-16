
# WCA Regulations Compiler

This is a tool to check, build, compare WCA Regulations and Guidelines and its translations.

## Install from PyPI

Install globally:

```shell
pip install wrc

# Run from the Python binary path:
wrc
wrc-states
```

If you use [`uv`](https://docs.astral.sh/uv/guides/tools/), you can also directly run the commands without installing:

```shell
uvx wrc
uvx --from wrc wrc-states
```

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
- To merge the Regulations and Guidelines into a single document (works with html, pdf and json targets):
`wrc path/to/wca-regulations --target=html --output=build --merged`
- When building translation it's necessary to provide the language (to choose the appropriate font/pdf names):
`wrc path/to/wca-regulations-translations/french --language=french --target=pdf --output=build`
- Check that a translation matches exactly the original rules:
`wrc path/to/wca-regulations-translations/french --diff=path/to/wca-regulations`

You can also take a look at the travis [script](https://github.com/thewca/wca-regulations-translations/blob/master/travis.sh) used in the translations repository.


## Running from the sources

The easiest way to develop locally is to use [`uv`](https://docs.astral.sh/uv/guides/tools/)

Run the compiler (outputs into `./build/` by default):

```shell
uv run wrc --target html -- ./test/samples/plus_n/wca-regulations.md
```

Process a states file (outputs into `./build/` by default):

```shell
uv run -- wrc-states ./test/samples/states/wca-states.md --target=json
```

## Deploying to PyPI

(section for maintainers in PyPI)

- Bump the version number in `pyproject-toml`
- `make publish`
