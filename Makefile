PYTHON ?= python3

.PHONY: all build clean

all: build

build:
	$(PYTHON) src/build_tree_beta.py

clean:
	rm -f data/processed/trees_clean.json output/helsinki_trees_beta.html
