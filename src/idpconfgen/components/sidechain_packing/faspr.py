"""Use FASPR to build sidechains."""
from idpconfgen import Path, source_folder


faspr_dun2010bbdep_path = Path(
    source_folder,
    'components',
    'sidechain_packing',
    'dun2010bbdep.bin',
    )


def init_faspr_sidechains(input_seq):
    """
    Instantiate dedicated function environment for FASPR sidehchain calculation.

    Examples
    --------
    >>> calc_faspr = init_fastpr_sidechains('MASFRTPKKLCVAGG')
    >>> # a (N, 3) array with the N,CA,C,O coordinates
    >>> coords = np.array( ... )
    >>> calc_faspr(coords)

    Parameters
    ----------
    input_seq : str
        The FASTA sequence of the protein for which this function will
        be used.

    Returns
    -------
    np.ndarray (M, 3)
        Heavy atom coordinates of the protein sequence.
    """
    # TODO:
    # this is here because tox is not able to detect idpcpp module.
    # this is a turnaround to allow tests to pass.
    # currently tests to not test this function.
    import idpcpp
    faspr_func = idpcpp.faspr_sidechains
    faspr_dun2010_bbdep_str = str(faspr_dun2010bbdep_path)

    def compute_faspr_sidechains(coords):
        """Do calculation."""
        return faspr_func(coords, input_seq, faspr_dun2010_bbdep_str)

    return compute_faspr_sidechains
