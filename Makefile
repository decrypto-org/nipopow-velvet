SOURCES := $(shell find . -iname '*.tex' -o -iname '*.bib' -o -iname '*.sty' -o -ipath '*figures/*.pdf')

.PHONY: all clean

all: main.pdf

main.pdf: $(SOURCES)
	rm -f *.glsdefs
	pdflatex main.tex
	bibtex main
	pdflatex main.tex
	pdflatex main.tex

clean:
	rm -f *.aux *.log *.out *.cfg *.glo *.idx *.toc *.ilg *.ind *.lof *.lot *.bbl *.blg *.gls *.cut *.hd *.dvi *.ps *.thm *.rpi *.d *.fls *.pyc *.fdb_latexmk *.sls *.slo *.slg *.glsdefs *.gls *.glg *.glo *.ist
	rm -Rf latex.out
	rm -Rf main.pdf
