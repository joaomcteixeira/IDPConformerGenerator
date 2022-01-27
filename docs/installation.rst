============
Installation
============

How to install the current beta-version:

1. Clone this repository::

    git clone https://github.com/julie-forman-kay-lab/IDPConformerGenerator

And navigate to the new ``IDPConformerGenerator`` folder::

    cd IDPConformerGenerator

2. Install the required dependencies manually, by creating a dedicated environment in your Anaconda::

    conda env create -f requirements.yml

If you don't Anaconda to manage your Python installations, and have difficulties
installing ``IDPConfGen``, raise an Issue in the main GitHub repository, and we
will help you.

3. Activate the new conda environment::

    conda activate idpconfgen

4. Install IDPConfGen in development mode in order for your installation to be
always up-to-date with the repository::

    python setup.py develop --no-deps

Likely, you will see a strange output message, never mind. Try running
IDPConfGen::

    idpconfgen -h

In case the above commands fails, let us know.

5. To update to the latest version, navigate to the IDPConfgen repository folder
in your computer and run::

    git pull

The IDPConfGen updates will be readily available in your computer.
