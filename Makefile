.PHONY: tests clean

tests:
	python3 -m pytest -W ignore::DeprecationWarning

coverage: .coverage
	coverage run tests/test_rss.py

report: coverage
	coverage html && open htmlcov/index.html

clean:
	black *.py tests/*.py
