PYTHON := python3
VENV_PYTHON := .venv/bin/python

.PHONY: all real logic venv test clean

all:
	$(VENV_PYTHON) scripts/run_real_pipeline.py
	$(PYTHON) scripts/run_logic_campaign.py

real:
	$(VENV_PYTHON) scripts/run_real_pipeline.py

logic:
	$(PYTHON) scripts/run_logic_campaign.py

venv:
	python3 -m venv .venv
	$(VENV_PYTHON) -m pip install pyyaml asn1tools scapy

test:
	$(PYTHON) -m unittest discover -s tests

clean:
	find outputs -type f -delete
	find corpus/real -type f -name '*.md' -delete
