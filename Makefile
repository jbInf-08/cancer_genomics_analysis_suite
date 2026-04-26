.PHONY: setup test train-smoke

setup:
	python -m pip install --upgrade pip
	pip install -e .

test:
	pytest CancerGenomicsSuite/tests -v

train-smoke:
	pytest CancerGenomicsSuite/tests/unit -v -m "critical or not slow"
