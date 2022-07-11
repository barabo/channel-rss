PYTEST_OPTS := -m pytest

.PHONY: tests clean

tests: clean
	python3 ${PYTEST_OPTS}

.coverage: tests/test_rss.py
	coverage run ${PYTEST_OPTS} tests/test_rss.py

report: .coverage
	coverage html && open htmlcov/index.html

clean:
	black *.py tests/*.py
