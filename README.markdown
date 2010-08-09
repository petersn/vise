
Vise
----

Vise is a simple, cowardly package manager.
Primarily, Vise tries as hard as possible to never ever break or destroy anything.
To this end, Vise employs many checks and heuristics to prevent accidental deletion of files, and the like.
A result of this is that running arbitrary, poorly constructed packages should be quite safe.
Thus, Vise is the community package manager, where anyone may upload a package that solves some bug, or implements some tweak.

Installation
------------

Download main.py (which is itself Vise) and use it to install the most recent version of itself by running:

	python main.py reset
	python main.py refresh
	python main.py install vise

Vise should now be installed. To update Vise, you may now run:

	vise upgrade vise

