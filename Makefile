.PHONY: dev-dependencies update-dependencies test docs fix check typing lint format ci-test ci-coverage poetry-export gh-pages

#########################
###### dev commands #####
#########################
dev-dependencies:
	poetry install --with dev --no-root

update-dependencies:
	poetry update --with dev

test:
	poetry run pytest -n auto --cov

docs:
	poetry run mkdocs serve

fix:
	poetry run ruff check . --fix
	poetry run ruff format .

check: poetry-export
	tox

typing: poetry-export
	tox -e typing

lint: poetry-export
	tox -e lint

format: poetry-export
	tox -e format


#########################
#### Helper commands ####
#########################
poetry-export:
	poetry export -f requirements.txt --output /tmp/requirements.txt --with dev


#########################
###### CI commands ######
#########################
ci-test:
	poetry run pytest

ci-coverage:
	poetry run pytest --cov --cov-report lcov


gh-pages:
	@echo "Updating gh-pages branch"
	@git checkout gh-pages || git checkout -b gh-pages
	@poetry run mkdocs build
	@cp -r site/* .
	@rm -rf site
	@git add .
	@git commit -m "Update documentation"
	@git push origin gh-pages
	@git checkout -
	@echo "gh-pages branch updated successfully"