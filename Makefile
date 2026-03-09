PYTHON := python3
VENV_PYTHON := .venv/bin/python

.PHONY: all real logic venv slice extract validate retrieve graph formal properties paths mermaid seeds test clean

all:
	$(PYTHON) scripts/run_pipeline.py

real:
	$(VENV_PYTHON) scripts/run_real_pipeline.py

logic:
	$(PYTHON) scripts/run_logic_campaign.py

venv:
	python3 -m venv .venv
	$(VENV_PYTHON) -m pip install pyyaml asn1tools scapy

slice:
	$(PYTHON) scripts/slice_procedures.py

extract:
	$(PYTHON) scripts/extract_efsm.py

validate:
	$(PYTHON) scripts/validate_efsm.py

retrieve:
	$(PYTHON) scripts/retrieve.py "RRC resume fullConfig"

graph:
	$(PYTHON) scripts/build_graph.py

formal:
	$(PYTHON) scripts/export_formal.py

properties:
	$(PYTHON) scripts/check_properties.py

paths:
	$(PYTHON) scripts/generate_paths.py

mermaid:
	$(PYTHON) scripts/render_mermaid.py

seeds:
	$(PYTHON) scripts/generate_seeds.py

test:
	$(PYTHON) -m unittest discover -s tests

clean:
	find outputs -type f -delete
	find corpus/slices -type f -delete
