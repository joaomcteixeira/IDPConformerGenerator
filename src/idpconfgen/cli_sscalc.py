"""
Extracts secondary structure information from PDBs.

Uses an external third party software.

USAGE:
    $ idpconfgen sscalc [PDBS]
"""
import argparse
import shutil
import traceback
from functools import partial
from multiprocessing import Pool
from pprint import pprint
from copy import copy

from idpconfgen import Path, log
from idpconfgen.libs import libcli
from idpconfgen.libs.libio import (
    extract_from_tar,
    read_path_bundle,
    read_dictionary_from_disk,
    )
from idpconfgen.libs.libmulticore import pool_chunks_to_disk_and_data_at_the_end, pool_function, consume_iterable_in_list
from idpconfgen.libs.libparse import mkdssp_w_split
from idpconfgen.logger import S, T, init_files
from idpconfgen.libs.libio import save_dictionary, save_pairs_to_disk
from idpconfgen.libs.libtimer import ProgressWatcher


LOGFILESNAME = '.idpconfgen_sscalc'
TMPDIR = '__tmpsscalc__'

_name = 'sscalc'
_help = 'Calculate secondary structure profile.'

_prog, _des, _us = libcli.parse_doc_params(__doc__)

ap = libcli.CustomParser(
    prog=_prog,
    description=libcli.detailed.format(_des),
    usage=_us,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    )

libcli.add_argument_cmd(ap)
libcli.add_argument_pdb_files(ap)

ap.add_argument(
    '-o',
    '--output',
    help=(
        "A path to the file where the PDBID secondary structure and FASTA"
        " information dictionary will be saved. "
        "Defaults to sscalc.json."
        ),
    type=Path,
    default='sscalc.json',
    action=libcli.CheckExt({'.json'}),
    )

# can't use the libcli option because this one is different
ap.add_argument(
    '-d',
    '--destination',
    help=(
        'Destination folder where the split PDB files will be stored. '
        'Defaults to current working directory.'
        'Alternatively, you can provide a path to a .tar file '
        'where PDBs will be saved.'
        ),
    type=Path,
    default='sscalc_splitted.tar',
    )

libcli.add_argument_reduced(ap)
libcli.add_argument_chunks(ap)
#libcli.add_argument_update(ap)  # discarded for now
libcli.add_argument_ncores(ap)


# add posibilitiy not to split???
def main(
        cmd,
        pdb_files,
        chunks=1000,
        destination='sscalc_splitted.tar',
        func=None,
        minimum=2,
        ncores=1,
        output='sscalc_output.json',
        reduced=False,
        **kwargs,
        ):
    """
    Run main cli logic.

    Parameters
    ----------
    ss_cmd : str or Path
        The command to run with subprocess module.

    pdbs : list
        A list of paths to PDB files or PDB file lists.

    output : string or Path, optional
        If given prints output to that file, else prints to console.
        Defaults to `None`.

    ncores : int
        The numbers of cores to use.
    """
    log.info(T('Extracting Secondary structure information'))
    init_files(log, LOGFILESNAME)

    log.info(T('reading input paths'))
    try:
        pdbs2operate = extract_from_tar(pdb_files, output=TMPDIR, ext='.pdb')
        _istarfile = True
    except TypeError:
        pdbs2operate = list(read_path_bundle(pdb_files, ext='pdb'))
        _istarfile = False
    log.info(S('done'))

    log.info(T('preparing task execution'))

    try:
        execute = partial(
            #pool_function,
            consume_iterable_in_list,
            #pdbs2operate, # items
            # args to consume_iterable_in_list
            mkdssp_w_split,
            #ncores=ncores,
            # kwargs for mkdssp function
            cmd=cmd,
            #destination=destination,
            reduced=reduced,
            minimum=minimum,
            )

        #d_ = {k: v for L in execute() for k, v in L}
        #save_dictionary(d_, output)

        tasks = pdbs2operate
        dssp_data = {}
        pdb_data = {}
        with ProgressWatcher(tasks) as pw:
            for i in range(0, len(tasks), chunks):
                task = tasks[i: i + chunks]
                with Pool(ncores) as pool:
                    imap = pool.imap_unordered(execute, task)
                    for result in imap:
                        for fname, dsspdict, pdb_split in result:
                            dssp_data[fname] = dsspdict
                            pdb_data[copy(fname)] = pdb_split
                        pw.increment()
                save_pairs_to_disk(pdb_data.items(), destination=destination)
                pdb_data.clear()
        save_dictionary(dssp_data, output)

    except Exception as err:
        log.error('FAILED')
        log.debug(traceback.format_exc())
        raise err
    finally:
        if _istarfile:
            shutil.rmtree(TMPDIR)
    return


if __name__ == '__main__':
    libcli.maincli(ap, main)
