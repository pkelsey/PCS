#
#
# File: $Id: Makefile,v 1.2 2006/06/15 07:52:02 gnn Exp $
#
# Author: George V. Neville-Neil
#
# Makefile for building distributions of PCS.  

PYTHON	= python

all: 
	$(PYTHON) setup.py config $(CONFIG_ARGS)
	$(PYTHON) setup.py build

install: all
	$(PYTHON) setup.py install

dist:
	$(PYTHON) setup.py sdist

clean:
	$(PYTHON) setup.py clean
	rm -rf build dist MANIFEST \
		pcs/pcap/pcap.c \
		pcs/pcap/config.h \
		pcs/pcap/config.pkl

