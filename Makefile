.PHONY: install test run-mcp run-sim run seed reset clean

install:
	pip install -r requirements-dev.txt

test:
	pytest -q

# Terminal 1
run-mcp:
	python -m freshkeep.mcpserver

# Terminal 2
run-sim:
	python -m freshkeep.simulator.app

# Both together (foreground, Ctrl-C stops both)
run:
	@sh -c 'python -m freshkeep.mcpserver & python -m freshkeep.simulator.app'

seed:
	curl -s -X POST http://127.0.0.1:8800/api/seed

reset:
	curl -s -X POST http://127.0.0.1:8800/api/reset

clean:
	rm -rf data/household.json data/audit.log
