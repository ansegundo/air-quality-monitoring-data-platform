def test_can_import_packages():
    """Verify that core packages can be imported without errors."""
    import api
    import ingest

    assert ingest is not None
    assert api is not None
