from buckteeth.knowledge.payer_rules import PayerRuleRepository


def test_get_frequency_limit():
    repo = PayerRuleRepository()
    limit = repo.get_frequency_limit("delta_dental", "D1110")
    assert limit is not None
    assert limit.max_per_period > 0


def test_check_frequency_ok():
    repo = PayerRuleRepository()
    result = repo.check_frequency("delta_dental", "D1110", months_since_last=7)
    assert result.allowed is True


def test_check_frequency_too_soon():
    repo = PayerRuleRepository()
    result = repo.check_frequency("delta_dental", "D1110", months_since_last=3)
    assert result.allowed is False
    assert "frequency" in result.reason.lower()


def test_get_bundling_rules():
    repo = PayerRuleRepository()
    rules = repo.get_bundling_rules("D2950")
    assert len(rules) > 0


def test_unknown_payer_returns_defaults():
    repo = PayerRuleRepository()
    limit = repo.get_frequency_limit("unknown_payer", "D1110")
    assert limit is not None
