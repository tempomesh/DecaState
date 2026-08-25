PYTHON := .venv/bin/python

.PHONY: doctor test smoke e2e phase1 bench-long checkpoint fork demo public-demo cow-benchmark production-check ui

ui:
	.venv/bin/python -m http.server 4173 --bind 127.0.0.1

doctor:
	$(PYTHON) -m decastate.cli.main doctor

test:
	$(PYTHON) -m pytest -q

smoke:
	$(PYTHON) -m decastate.cli.main run 'Reply with exactly: DECASTATE_OLLAMA_OK' --model qwen2.5:14b

e2e:
	./scripts/e2e_real_ollama.sh

phase1:
	./scripts/run_phase1.sh

bench-long:
	$(PYTHON) experiments/03_long_context_resume.py

checkpoint:
	$(PYTHON) experiments/04_checkpoint_rollback.py

fork:
	$(PYTHON) experiments/05_fork_baseline.py

demo:
	$(PYTHON) experiments/06_coding_agent_demo.py

public-demo:
	./scripts/public_demo.sh

cow-benchmark:
	$(PYTHON) experiments/07_cow_benchmark.py

production-check:
	./scripts/production_check.sh
