watch:
	watchfiles "uv run pytest -q -s" src   

test:
	pytest -s

sync:
	python sync.py

run:
	streamlit run main.py

PHONY:
