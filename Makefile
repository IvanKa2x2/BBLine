venv:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip

install:
	pip install -r requirements-dev.txt

lint:
	ruff .

format:
	black .

test:
	pytest

typecheck:
	mypy .

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run:
	python bbline.py

db-dump:
	sqlite3 db/bbline.sqlite .dump > db/bbline_dump.sql

pull:
	git pull

push:
	git add .
	git commit -m "Auto-commit"
	git push

status:
	git status

all: lint format test typecheck
