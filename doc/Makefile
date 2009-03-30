all: index.html recipes.html examples.html

%.html : %.txt
	rst2html.py $< $@
