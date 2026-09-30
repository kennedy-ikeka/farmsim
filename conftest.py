import pytest

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