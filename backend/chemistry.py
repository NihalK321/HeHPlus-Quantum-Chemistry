"""Build short linear peptides and evaluate a restricted set of shapes.

MMFF94 is a classical molecular mechanics model, not an electronic-structure
calculation. All unselected coordinates remain at a seeded embedded geometry.
There is no solvent model, structural relaxation, or activity prediction.
"""

from dataclasses import dataclass
from itertools import product
from math import isfinite

from rdkit import Chem
from rdkit.Chem import AllChem, rdMolTransforms

from .schema import Configuration, OptimizationRequest, Torsion


@dataclass
class ChemistryProblem:
    sequence: str
    torsions: list[Torsion]
    configurations: list[Configuration]
    structures: dict[str, str]
    pdb_structures: dict[str, str]


def _backbone_torsions(molecule) -> list[Torsion]:
    """Find phi/psi torsions, excluding rotation around ring bonds."""
    residues = {}
    for atom in molecule.GetAtoms():
        info = atom.GetPDBResidueInfo()
        if info is not None:
            residues.setdefault(info.GetResidueNumber(), {})[info.GetName().strip()] = atom.GetIdx()

    torsions = []
    for number, atoms in sorted(residues.items()):
        candidates = []
        if number - 1 in residues:
            candidates.append(("phi", (residues[number - 1]["C"], atoms["N"], atoms["CA"], atoms["C"])))
        if number + 1 in residues:
            candidates.append(("psi", (atoms["N"], atoms["CA"], atoms["C"], residues[number + 1]["N"])))
        for name, indices in candidates:
            if not molecule.GetBondBetweenAtoms(indices[1], indices[2]).IsInRing():
                torsions.append(Torsion(name=f"{name}_{number}", residue_number=number, atom_indices=indices))
    return torsions


def build_problem(request: OptimizationRequest) -> ChemistryProblem:
    """Enumerate 2**torsion_count configurations in increasing basis order.

    Molecules use free termini and RDKit's default protonation, with no assumed
    disulfide bridges or other modifications. Energies are comparable within
    this one molecule/geometry setup, not across different peptide sequences.
    """
    molecule = Chem.MolFromSequence(request.sequence)
    if molecule is None:
        raise ValueError("RDKit could not construct this peptide.")
    molecule = Chem.AddHs(molecule)
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = request.seed
    if AllChem.EmbedMolecule(molecule, parameters) != 0:
        raise ValueError("Could not generate a starting geometry; try another seed or shorter sequence.")

    available = _backbone_torsions(molecule)
    if request.torsion_count > len(available):
        raise ValueError(f"This peptide has only {len(available)} supported backbone torsions; reduce torsion_count.")
    torsions = available[:request.torsion_count]
    configurations = []
    structures = {}
    pdb_structures = {}
    for bits in product("01", repeat=request.torsion_count):
        bitstring = "".join(bits)
        angles = [request.angle_options[int(bit)] for bit in reversed(bits)]
        candidate = Chem.Mol(molecule)
        conformer = candidate.GetConformer()
        for torsion, angle in zip(torsions, angles):
            rdMolTransforms.SetDihedralDeg(conformer, *torsion.atom_indices, angle)
        properties = AllChem.MMFFGetMoleculeProperties(candidate, mmffVariant="MMFF94")
        if properties is None:
            raise ValueError("MMFF94 parameters are unavailable for this peptide.")
        force_field = AllChem.MMFFGetMoleculeForceField(candidate, properties)
        if force_field is None:
            raise ValueError("Could not create the MMFF94 energy model.")
        energy = float(force_field.CalcEnergy())
        if not isfinite(energy):
            raise ValueError("A configuration produced a non-finite energy; try other angles.")
        configurations.append(Configuration(bitstring=bitstring, angles_degrees=angles, energy_kcal_mol=energy))
        structures[bitstring] = Chem.MolToMolBlock(candidate)
        # Export directly from the molecule to preserve residue and atom names
        # for PDB viewers. Converting from MOL text would lose those labels.
        pdb_structures[bitstring] = Chem.MolToPDBBlock(candidate)
    return ChemistryProblem(request.sequence, torsions, configurations, structures, pdb_structures)
