"""Module that contains some simple smoke tests using `pytest_container
<https://github.com/dcermak/pytest_container/>`_.

"""

import pytest
from pytest_container import DerivedContainer
from pytest_container.container import ContainerData


_COMMAND_NOT_FOUND_BIN = "/src/target/debug/cnf-rs"

# containerfile that builds cnf-rs and sources the bash helper
_CONTAINERFILE = f"""RUN zypper -n in shadow rust libsolv-devel cargo clang-devel
WORKDIR /src/
ENV COMMAND_NOT_FOUND_BIN={_COMMAND_NOT_FOUND_BIN}
COPY . /src/
RUN cargo build && echo "source /src/command_not_found_bash" >> /etc/bash.bashrc
"""

# extension of the containerfile which runs as a different user
_USER_CONTAINERFILE = (
    _CONTAINERFILE
    + """RUN useradd -m geeko
USER geeko
"""
)

LEAP_15_5 = [
    DerivedContainer(
        base=base_url,
        containerfile=_CONTAINERFILE,
    )
    for base_url in (
        "registry.opensuse.org/opensuse/leap:15.5",
    )
]

TW_USR = [
    DerivedContainer(
        base=base_url,
        containerfile=_USER_CONTAINERFILE,
    )
    for base_url in (
        "registry.opensuse.org/opensuse/tumbleweed:latest",
    )
]

CONTAINER_IMAGES = [TW_USR, LEAP_15_5]


def test_cnf_finds_cmake(auto_container: ContainerData) -> None:
    """Smoke test checking whether :command:`cnf-rs cmake` outputs the expected
    string to stdout as indicated in the README.

    """
    res = auto_container.connection.run_expect([0], f"{_COMMAND_NOT_FOUND_BIN} cmake")
    assert "The program 'cmake' can be found in following packages:" in res.stdout
    assert (
        """Try installing with:
    sudo zypper install <selected_package>"""
        in res.stdout
    )


@pytest.mark.parametrize(
    "container", [TW_USR, LEAP_15_5], indirect=True
)
def test_cnf_finds_usr_sbin(container: ContainerData) -> None:
    """Check that :command:`cnf-rs zypp-refresh` executed as an unprivileged
    user will tell them that :command:`zypp-refresh` is installed in
    :file:`/usr/sbin/` and needs elevated privileges.

    """
    binary = "zypp-refresh"
    assert container.connection.find_command(binary)
    res = container.connection.run_expect([0], f"{_COMMAND_NOT_FOUND_BIN} {binary}")
    assert (
        f"Absolute path to '{binary}' is '/usr/sbin/{binary}', so running it may require superuser privileges (eg. root)."
        in res.stdout
    )


def test_cnf_finds_installed_pkg(auto_container: ContainerData) -> None:
    """Test whether :command:`cnf-rs bash` correctly tells the user that
    :command:`bash` is already present on their system.

    """
    assert auto_container.connection.exists("bash")
    res = auto_container.connection.run_expect([0], f"{_COMMAND_NOT_FOUND_BIN} bash")
    assert (
        "Absolute path to 'bash' is '/usr/bin/bash'. Please check your $PATH variable to see whether it contains the mentioned path"
        in res.stdout
    )
