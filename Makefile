PYTHON ?= python3
ID ?= EXP-001
STAGE ?= smoke

.PHONY: install validate test new lock implemented approve run bundle accept finalize context digest

install:
	@$(PYTHON) -m pip install -e ".[dev]"

validate:
	@$(PYTHON) scripts/validate.py

test:
	@$(PYTHON) -m pytest -q

new:
	@$(PYTHON) scripts/new_experiment.py --id $(ID) --stage $(STAGE)

lock:
	@$(PYTHON) scripts/lock_plan.py --id $(ID)

implemented:
	@$(PYTHON) scripts/mark_implemented.py --id $(ID)

approve:
	@$(PYTHON) scripts/approve_full.py --id $(ID)

run:
	@$(PYTHON) scripts/run_experiment.py --id $(ID)

bundle:
	@$(PYTHON) scripts/build_review_bundle.py --id $(ID)

accept:
	@$(PYTHON) scripts/accept_evaluation.py --id $(ID)

finalize:
	@$(PYTHON) scripts/finalize_experiment.py --id $(ID)

context:
	@$(PYTHON) scripts/build_context.py

digest:
	@$(PYTHON) scripts/build_digest.py
