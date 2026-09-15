PYTHON := .venv/bin/python

.PHONY: doctor test smoke e2e phase1 bench-long checkpoint fork demo tiny-demo step1 step2 step3 step4 step5 step6 step7 step8 step9 step10 step11 step12 step13 step14 step15 step16 step17 curriculum public-demo cow-benchmark production-check ui

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

tiny-demo:
	$(PYTHON) experiments/07_tiny_10param_llm.py

step1:
	$(PYTHON) experiments/08_step1_tokens_embeddings.py

step2:
	$(PYTHON) Experiment/02_embeddings_qkv.py

step3:
	$(PYTHON) Experiment/03_attention.py

step4:
	$(PYTHON) Experiment/04_transformer_layer.py

step5:
	$(PYTHON) Experiment/05_logits_next_token.py

step6:
	$(PYTHON) Experiment/06_training_loss_backprop.py

step7:
	$(PYTHON) Experiment/07_tiny_train_then_infer.py

step8:
	$(PYTHON) Experiment/08_finetuning_memory.py

step9:
	$(PYTHON) Experiment/09_multi_layer_forward.py

step10:
	$(PYTHON) Experiment/10_train_qkv_attention.py

step11:
	$(PYTHON) Experiment/11_tiny_generation_loop.py

step12:
	$(PYTHON) Experiment/12_toy_kv_cache_save_restore.py

step13:
	$(PYTHON) Experiment/13_advanced_fundamentals.py

step14:
	$(PYTHON) Experiment/14_attention_types.py

step15:
	$(PYTHON) Experiment/15_mha_gqa_mqa.py

step16:
	$(PYTHON) Experiment/16_dense_vs_moe.py

step17:
	$(PYTHON) Experiment/17_training_inference_memory.py

curriculum:
	$(PYTHON) Experiment/01_tokens_embeddings.py

public-demo:
	./scripts/public_demo.sh

cow-benchmark:
	$(PYTHON) experiments/07_cow_benchmark.py

production-check:
	./scripts/production_check.sh
