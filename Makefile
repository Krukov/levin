
LENGTH=120
SRC=levin
SPID=

.PHONY: run
run:
	python -m watchgod run.main

.PHONY: check
check:
	curl  --http2-prior-knowledge https://localhost:8000/test/  -H "Content-type: application/json"

.PHONY: profiling
profiling:
	profiling -S run.py

.PHONY: frame
frame:
	rm .pid
	SPID="$(shell python run.py & echo $$!)"
	echo $(SPID)
	docker run --rm -d  svagi/h2load -c 50 -n 20000 -m 10 -t 4 http://host.docker.internal:8000/
	sudo py-spy -d 3 -f profile.svg -p $(SPID)
	kill -9 $(SPID)

.PHONY: run
perf:
	docker run --rm -it  svagi/h2load -c 50 -n 20000 -m 10 -t 4 http://host.docker.internal:8000/-/

.PHONY: format
format: black isort

.PHONY: pylint
pylint:
	pylint $(SRC) --reports=n --max-line-length=$(LENGTH)

.PHONY: isort
isort:
	@echo -n "Run isort"
	isort --lines $(LENGTH) -rc $(SRC) tests

.PHONY: black
black:
	@echo -n "Run black"
	black -l $(LENGTH) $(SRC) tests

.PHONY: check-isort
check-isort:
	isort --lines $(LENGTH) -vb -rc --check-only -df $(SRC) tests

.PHONY: check-styles
check-styles:
	pycodestyle $(SRC) tests --max-line-length=$(LENGTH) --format pylint --exclude=migrations

.PHONY: check-black
check-black:
	black --check --diff -v -l $(LENGTH) $(SRC) tests

.PHONY: checks
checks: check-styles check-isort check-black pylint-score tests

.PHONY: tests
tests:
	pytest -v --cov=$(SRC) -v --cov-report=xml --cov-report=term

.PHONY: pylint-score
pylint-score:
	$(eval $@_SCORE := $(shell pylint --output-format=text --max-line-length=$(LENGTH) $(SRC) | sed -n 's/^Your code has been rated at \([-0-9.]*\)\/.*/\1/p'))
	@echo $($@_SCORE)
	@if [ $(shell echo "$($@_SCORE) < 9.90" | bc) -eq 1 ]; then exit 1; fi
	@anybadge --value=$($@_SCORE) -o --file=pylint.svg pylint


gen-cert:
	openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes