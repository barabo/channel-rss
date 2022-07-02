.PHONY: tests clean

tests:
	pytest

coverage: .coverage
	coverage run tests/test_rss.py

report: coverage
	coverage html && open htmlcov/index.html

clean:
	black *.py tests/*.py
