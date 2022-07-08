PYTEST_OPTS := -m pytest -W ignore::DeprecationWarning

.PHONY: tests clean

tests: clean
	python3 ${PYTEST_OPTS}

coverage: .coverage
	coverage run ${PYTEST_OPTS} tests/test_rss.py

report: coverage
	coverage html && open htmlcov/index.html

clean:
	black *.py tests/*.py
