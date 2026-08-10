def pytest_collection_modifyitems(config, items):
    only_items = [item for item in items if "only" in item.keywords]
    if only_items:
        items[:] = only_items