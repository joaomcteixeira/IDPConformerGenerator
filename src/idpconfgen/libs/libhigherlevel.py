"""
Higher level functions.

Function which operate with several libraries
and are defined here to avoid circular imports.
"""
from collections import defaultdict
from contextlib import suppress
from functools import reduce, partial

from idpconfgen import Path, log
from idpconfgen.core.definitions import blocked_ids
from idpconfgen.libs.libdownload import download_dispacher
from idpconfgen.libs.libio import concatenate_entries, read_PDBID_from_source, save_pairs_dispacher
from idpconfgen.libs.libparse import group_runs, group_by
from idpconfgen.libs.libpdb import PDBList, PDBIDFactory, atom_resSeq, atom_name
from idpconfgen.libs.libstructure import Structure, eval_bb_gaps, get_PDB_from_residues, col_resSeq
from idpconfgen.libs.libtimer import record_time
from idpconfgen.logger import S, T, init_files
from idpconfgen.libs.libmulticore import pool_function_in_chunks, consume_iterable_in_list



# USED OKAY!
def download_pipeline(func, logfilename='.download'):
    """
    Context pipeline to download PDB/mmCIF files.

    Exists because fetching and download filtered PDBs shared the same
    operational contextm, only differing on the function which
    orchestrates the download process.

    Parameters
    ----------
    func : function
        The actual function that orchestrates the download operation.

    logfilename : str, optional
        The common stem name of the log files.
    """
    LOGFILESNAME = logfilename
    def main(
            pdbids,
            chunks=5_000,
            destination=None,
            ncores=1,
            update=False,
            ):
        """Run main script logic."""
        init_files(log, LOGFILESNAME)

        #
        log.info(T('reading input PDB list'))

        pdblist = PDBList(concatenate_entries(pdbids))

        log.info(
            f"{S(str(pdblist))}\n"
            f"{S('done')}\n"
            )

        #
        log.info(T('Filtering input'))
        destination = destination or Path.cwd()
        log.info(
            f"{S(f'from destination: {destination}')}\n"
            f"{S('and other sources...')}"
            )

        # comparison block
        def diff(first, other):
            return first.difference(other)

        remove_from_input = [
            read_PDBID_from_source(destination),
            PDBList(blocked_ids),
            ]

        # yes, there are just two items in remove_from_input, why use reduce?
        # what if more are added in the future? :-P the engine is already created
        pdblist_comparison = reduce(diff, remove_from_input, pdblist)
        log.info(S(f'Found {str(pdblist_comparison)} to download'))
        #

        something_to_download = len(pdblist_comparison) > 0
        if something_to_download and update:

            execute = partial(
                pool_function_in_chunks,
                consume_iterable_in_list,
                list(pdblist_comparison.name_chains_dict.items()),
                func,
                ncores=ncores,
                chunks=chunks,
                )

            save_pairs = save_pairs_dispacher[destination]

            for chunk in execute():
                flatted = (item for result in chunk for item in result)
                save_pairs(flatted, destination)

            log.info(T('Reading UPDATED destination'))
            pdblist_updated = read_PDBID_from_source(destination)
            pdblist_up_comparison = pdblist.difference(pdblist_updated)
            log.info(S(f'{str(pdblist_up_comparison)}'))
            if len(pdblist_up_comparison) > 0:
                log.info(S(
                    'There are PDBIDs not downloaded\n.'
                    'Those IDs have been registered in the '
                    f'{LOGFILESNAME}.debug file.'
                    ))
                log.debug('\n'.join(str(_id) for _id in pdblist_up_comparison))

        elif not something_to_download and update:
            log.info(S('There is nothing to download.'))
            log.info(S('All requested IDs are already at the destination folder.'))

        log.info(T('PDB Downloader finished'))
        return

    return main


def get_fastas(pdbid, mdict=None):
    pdbname = Path(pdbid[0]).stem
    pdbdata = pdbid[1]
    structure = Structure(pdbdata)
    structure.build()
    fasta = structure.fasta
    assert len(fasta) == 1
    mdict[str(PDBIDFactory(pdbname))] = next(iter(fasta.values()))
    #out_data.append('{}|{}'.format(pdbid, next(iter(fasta.values()))))

    return


def split_backbone_segments(
        pdbid,
        mfiles=None,
        mdata=None,
        minimum=2,
        sscalc_data=None,
        ):
    """
    """
    pdbname = Path(pdbid[0]).stem
    pdbdata = pdbid[1]
    pdb_dssp_data = sscalc_data[pdbname]
    residues = pdb_dssp_data['resids'].split(',')
    dssp_residues = [int(i) for i in residues]
    residues_groups = [[str(i) for i in seg] for seg in group_runs(dssp_residues)]
    structural_data = [k for k in pdb_dssp_data.keys() if k != 'resids']
    #splitdata = defaultdict(dict)
    for i, segment in enumerate(residues_groups):
        key = f'{pdbname}_seg{i}'
        for datatype in structural_data:
            mdata[key][datatype] = \
                ''.join(
                    c
                    for res, c in zip(residues, pdb_dssp_data[datatype])
                    if res in segment
                    )
        mdata[key]['resids'] = ','.join(segment)

        #structure = Structure(pdbdata)
        #structure.build()
        #structure.add_filter(lambda x: x[col_resSeq] in segment)
        #_mfiles[f'{key}.pdb'] = '\n'.join(structure.get_PDB())
        segset = set(segment)
        mfiles[f'{key}.pdb'] = b'\n'.join(line for line in pdbdata.split(b'\n') if line[atom_resSeq].strip() in segset)


def _split_backbone_segments(
        pdbid,
        mfiles,
        sscalc_data=None,
        mdata=None,
        minimum=2,
        ):
    """
    Parameters
    ----------
    pdbid : tuple (str, str)

    mfiles : `multiprocessing.Manager.dict`

    mdata : `multiprocessing.Manager.dict`, optional

    minimum : int, optional
        The minimum size of each segment.
        Defaults to 2.

    sscalc_data : dict, optional
    """
    pdbname = Path(pdbid[0]).stem
    pdbdata = pdbid[1]
    structure = Structure(pdbdata)
    structure.build()

    # this might be slightly slower but it definitively more modular
    # and testable
    # `structure_segments` are in residue number (str)
    structure_segments = eval_bb_gaps(structure, minimum=2)
    assert isinstance(structure_segments, list)

    # here I have to put them in the mfiles
    if sscalc_data:
        dssp_segments, structure_segments = split_sscalc_data(
            pdbname,
            sscalc_data,
            structure_segments,
            )
        assert len(dssp_segments) == len(structure_segments), pdbname
        mdata.update(dssp_segments)

    splitted_segments = \
        list(get_PDB_from_residues(structure, structure_segments))

    assert len(structure_segments) == len(splitted_segments), pdbname
    for i, txt in enumerate(splitted_segments):
        mfiles[f'{pdbname}_seg{i}'] = txt


def split_sscalc_data(pdbname, data, segments):
    """
    To do.
    """
    pdb_dssp_data = data[pdbname]
    structural_data = [k for k in pdb_dssp_data.keys() if k != 'resids']

    # residues as identified by DSSP
    residues = pdb_dssp_data['resids'].split(',')
    assert all(s.isdigit() for s in residues), pdbname

    splitdata = defaultdict(dict)
    segs_in_dssp = []

    for i, segment in enumerate(segments):

        assert all(s.isdigit() for s in segment), pdbname
        # this is done with list instead of sets because I want to keep order
        # two reduction step

        # reduces residues in DSSP to the residues in the segment
        reduction = [res for res in residues if res in segment]

        # some residues can be in the DSSP and not on the segment
        # residues in the segment must be reduced accordingly
        segs_in_dssp.append([res for res in segment if res in reduction])
        assert len(reduction) == len(segs_in_dssp[-1])

        key = f'{pdbname}_seg{i}'
        for datatype in structural_data:
            splitdata[key][datatype] = \
                ''.join(
                    c
                    for res, c in zip(residues, pdb_dssp_data[datatype])
                    if res in reduction
                    )

        assert all(
            len(value) == len(reduction)
            for value in splitdata[key].values()
            ), pdbname

        splitdata[key]['resids'] = ','.join(reduction)

    return splitdata, segs_in_dssp


# USED OKAY
def extract_secondary_structure(
        pdbid,
        ssdata,
        atoms='all',
        minimum=0,
        structure='all',
        ):
    """
    Extract secondary structure elements from PDB data.

    Parameters
    ----------
    pdbid : tuple
        Where index 0 is the PDB id code, for example `12AS.pdb`, or
        `12AS_A`, or `12AS_A_seg1.pdb`.
        And, index 1 is the PDB data itself in bytes.

    ssdata : dict
        Dictionary containing the DSSP information. Must contain a key
        equal to `Path(pdbid).stem, where `dssp` key contains the DSSP
        information for that PDB.

    atoms : str or list of str or bytes, optional
        The atom names to keep.
        Defaults to `all`.
    """
    pdbname = Path(pdbid[0]).stem
    pdbdata = pdbid[1].split(b'\n')
    pdbdd = ssdata[pdbname]

    ss_identified = set(pdbdd['dssp'])
    if structure == 'all':
        ss_to_isolate = ss_identified
    else:
        ss_to_isolate = set(s for s in ss_identified if s in structure)

    # general lines filters
    line_filters = []
    LF_append = line_filters.append
    LF_pop = line_filters.pop

    # in atoms filter
    if atoms != 'all':
        with suppress(AttributeError):  # it is more common to receive str
            atoms = [c.encode() for c in atoms]
        line_filters.append(lambda x: x[atom_name].strip() in atoms)

    dssp_slices = group_by(pdbdd['dssp'])
    # DR stands for dssp residues
    DR = [c.encode() for c in pdbdd['resids'].split(',')]

    for ss in ss_to_isolate:

        ssfilter = (slice_ for char, slice_ in dssp_slices if char == ss)
        minimum_size = (s for s in ssfilter if s.stop - s.start >= minimum)

        for counter, seg_slice in enumerate(minimum_size):

            LF_append(lambda x: x[atom_resSeq].strip() in DR[seg_slice])
            pdb = b'\n'.join(l for l in pdbdata if all(f(l) for f in line_filters))
            LF_pop()

            yield f'{pdbname}_{ss}_{counter}.pdb', pdb

            counter += 1
