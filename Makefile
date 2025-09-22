PYTHON ?= python3

.PHONY: test test-acceptance test-contracts test-resilience coverage

test:
	$(PYTHON) -m pytest -m "not slow"

test-acceptance:
	$(PYTHON) -m pytest -m acceptance

test-contracts:
	$(PYTHON) -m pytest -m contracts

test-resilience:
	$(PYTHON) -m pytest -m resilience

coverage:
	$(PYTHON) -m pytest --cov=core --cov=experiment_agents --cov=utils
