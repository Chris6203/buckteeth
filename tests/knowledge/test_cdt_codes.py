import pytest
from buckteeth.knowledge.cdt_codes import CDTCodeRepository


@pytest.fixture
def repo():
    return CDTCodeRepository()


def test_lookup_exact_code(repo):
    result = repo.lookup("D2393")
    assert result is not None
    assert result.code == "D2393"
    assert result.category == "restorative"


def test_search_by_keyword(repo):
    results = repo.search("composite posterior")
    assert len(results) > 0
    assert any(r.code.startswith("D239") for r in results)


def test_search_by_category(repo):
    results = repo.search_by_category("preventive")
    assert len(results) > 0
    assert all(r.category == "preventive" for r in results)


def test_get_candidates_for_procedure(repo):
    candidates = repo.get_candidates("MOD composite restoration posterior tooth")
    assert len(candidates) > 0
    assert len(candidates) <= 10


def test_unknown_code_returns_none(repo):
    result = repo.lookup("D9999")
    assert result is None
