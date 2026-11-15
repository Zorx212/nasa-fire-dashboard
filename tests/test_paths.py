from src import paths


def test_output_paths_live_under_data_processed() -> None:
    assert paths.INSIGHTS_PATH == paths.PROCESSED_DIR / "insights.json"
    assert paths.REJECTED_PATH == paths.PROCESSED_DIR / "rejected.json"
    assert paths.PROCESSED_DIR == paths.PROJECT_ROOT / "data" / "processed"


def test_catalog_path_is_data_catalog_csv() -> None:
    assert paths.CATALOG_PATH == paths.PROJECT_ROOT / "data" / "catalog.csv"


def test_every_path_is_inside_the_project() -> None:
    for path in (
        paths.RAW_DIR,
        paths.TEXT_DIR,
        paths.CACHE_DIR,
        paths.PROCESSED_DIR,
        paths.CATALOG_PATH,
        paths.INSIGHTS_PATH,
        paths.REJECTED_PATH,
    ):
        assert paths.PROJECT_ROOT in path.parents
