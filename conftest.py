from shutil import rmtree

import pytest

from utils.config import TMP_DIR

def pytest_collection_modifyitems(config, items):
    only_tests = [
        item for item in items
        if item.get_closest_marker("only")
    ]

    if not only_tests:
        return

    only_nodeids = {item.nodeid for item in only_tests}

    skip_other_tests = pytest.mark.skip(
        reason="Skipped because another test is marked with @pytest.mark.only"
    )

    for item in items:
        if item.nodeid not in only_nodeids:
            item.add_marker(skip_other_tests)

@pytest.fixture(scope="session", autouse=True)
def clean_tmp():
    yield
    rmtree(TMP_DIR, ignore_errors=True)