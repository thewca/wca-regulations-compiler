import subprocess

# We assume this is being run from the project root directory.
process = subprocess.run(
    [
        "uv",
        "run",
        "wrc",
        "--target",
        "html",
        "--",
        "test/samples/mixed-guidelines-format/wca-regulations.md",
    ],
    check=False,
    capture_output=True,
)

assert process.returncode == 1, "Expected failure."
assert "Saw a multiplus format guideline after a +n guideline" in str(process.stdout), (
    "Did not see expected failure message."
)
