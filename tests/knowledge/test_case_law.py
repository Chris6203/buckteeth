from buckteeth.knowledge.case_law import CaseLawRepository


def test_search_by_denial_reason():
    repo = CaseLawRepository()
    results = repo.search_by_denial_code("CO-45")
    assert len(results) > 0


def test_search_by_keyword():
    repo = CaseLawRepository()
    results = repo.search("medical necessity")
    assert len(results) > 0


def test_search_by_state():
    repo = CaseLawRepository()
    results = repo.search_by_state("CA")
    assert len(results) > 0


def test_get_relevant_citations():
    repo = CaseLawRepository()
    citations = repo.get_relevant_citations(
        denial_code="CO-50",
        procedure_code="D2740",
        state="CA",
    )
    assert len(citations) > 0
    assert all(c.citation is not None for c in citations)
