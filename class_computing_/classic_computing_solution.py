"""Represent peptide sequences for the classical computing solution."""


# The 20 standard amino acids: one-letter code -> (name, three-letter code).
AMINO_ACIDS = {
    "A": ("Alanine", "Ala"),
    "R": ("Arginine", "Arg"),
    "N": ("Asparagine", "Asn"),
    "D": ("Aspartic acid", "Asp"),
    "C": ("Cysteine", "Cys"),
    "E": ("Glutamic acid", "Glu"),
    "Q": ("Glutamine", "Gln"),
    "G": ("Glycine", "Gly"),
    "H": ("Histidine", "His"),
    "I": ("Isoleucine", "Ile"),
    "L": ("Leucine", "Leu"),
    "K": ("Lysine", "Lys"),
    "M": ("Methionine", "Met"),
    "F": ("Phenylalanine", "Phe"),
    "P": ("Proline", "Pro"),
    "S": ("Serine", "Ser"),
    "T": ("Threonine", "Thr"),
    "W": ("Tryptophan", "Trp"),
    "Y": ("Tyrosine", "Tyr"),
    "V": ("Valine", "Val"),
}


class Peptide:
    """A peptide whose amino acids are stored in order, from N- to C-terminus."""

    def __init__(self):
        self.amino_acids: list[str] = []

    def add_amino_acid(self, amino_acid: str) -> None:
        """Append an amino acid, using a name or code such as 'alanine' or 'A'."""
        if not isinstance(amino_acid, str):
            raise TypeError("An amino acid must be supplied as a string.")
        amino_acid = amino_acid.strip()
        if not amino_acid:
            raise ValueError("An amino acid cannot be empty.")
        self.amino_acids.append(amino_acid)

    def __len__(self) -> int:
        """Return the number of amino acids in the peptide."""
        return len(self.amino_acids)

    @property
    def sequence(self) -> str:
        """Return one-letter codes, accepting stored names or either code format."""
        choices = {}
        for code, (name, abbreviation) in AMINO_ACIDS.items():
            for label in (code, name, abbreviation):
                choices[label.casefold()] = code

        codes = []
        for amino_acid in self.amino_acids:
            code = choices.get(amino_acid.strip().casefold())
            if code is None:
                raise ValueError(f"Unrecognized amino acid: {amino_acid!r}")
            codes.append(code)
        return "".join(codes)


class PeptideTable:
    """Small reference table indexed by complete N-to-C amino-acid sequences.

    This matches sequences only; it does not predict biological activity or
    verify modifications, stereochemistry, or three-dimensional structure.
    """

    def __init__(self):
        self.peptides = {
            "CYIQNCPLG": {
                "name": "Oxytocin",
                "effect": "Promotes uterine contractions and milk ejection.",
                "structure_notes": (
                    "The native peptide has a disulfide bond between cysteines "
                    "1 and 6 and an amidated C-terminus."
                ),
                "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/439302",
            },
            "CYFQNCPRG": {
                "name": "Arginine vasopressin (ADH)",
                "effect": (
                    "Promotes water retention by the kidneys and can constrict "
                    "blood vessels."
                ),
                "structure_notes": (
                    "The native peptide has a disulfide bond between cysteines "
                    "1 and 6 and an amidated C-terminus."
                ),
                "source_url": "https://shop.bachem.com/product/4012215/",
            },
            "YGGFM": {
                "name": "Met-enkephalin",
                "effect": "An endogenous opioid peptide involved in modulating pain signaling.",
                "structure_notes": (
                    "The reference peptide is linear, with a free N-terminus "
                    "and a C-terminal carboxyl group."
                ),
                "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/443363",
                "effect_source_url": "https://doi.org/10.1063/1.3186747",
            },
            "YADAIFTNSYRKVLGQLSARKLLQDIMSRQQGESNQERGARARL": {
                "name": "Tesamorelin",
                "effect": "A growth-hormone-releasing hormone analogue that stimulates growth-hormone release.",
                "structure_notes": (
                    "44-residue backbone; the reference molecule has an N-terminal "
                    "trans-3-hexenoyl group and an amidated C-terminus. "
                    "Backbone sequence alone does not distinguish it from native GHRH(1-44)."
                ),
                "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/Tesamorelin",
            },
            "HAEGTFTSDVSSYLEGQAAKEFIAWLVRGRG": {
                "name": "Liraglutide",
                "effect": "A GLP-1 receptor agonist involved in regulating insulin secretion and appetite.",
                "structure_notes": (
                    "31-residue backbone; a C16 fatty-acid chain is attached through "
                    "a glutamate linker to lysine 20 (GLP-1 numbering: lysine 26)."
                ),
                "source_url": "https://www.acs.org/content/dam/acsorg/acs-webinars/2019/slides/2019-10-24-ddds10-semaglutide.pdf",
                "effect_source_url": "https://www.niddk.nih.gov/health-information/weight-management/prescription-medications-treat-overweight-obesity",
            },
            "HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS": {
                "name": "Exenatide",
                "effect": "A GLP-1 receptor agonist that enhances glucose-dependent insulin secretion.",
                "structure_notes": "39-residue peptide with an amidated C-terminus.",
                "source_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/209210s024lbl.pdf",
                "sequence_source_url": "https://doi.org/10.1080/10826076.2025.2502034",
            },
        }
        # These cannot be represented faithfully using only the standard 20.
        # Keep them as name-only references rather than substituting residues.
        self.name_only_peptides = {
            "carnosine": {
                "name": "Carnosine",
                "effect": "Helps buffer changes in muscle pH.",
                "structure_notes": (
                    "A dipeptide of beta-alanine and L-histidine. Beta-alanine is "
                    "not the standard alpha-alanine represented by A; this is not AH."
                ),
                "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/Carnosine",
                "effect_source_url": "https://ods.od.nih.gov/factsheets/ExerciseAndAthleticPerformance-HealthProfessional/",
            },
            "semaglutide": {
                "name": "Semaglutide",
                "effect": "A GLP-1 receptor agonist involved in regulating insulin secretion and appetite.",
                "structure_notes": (
                    "31 residues, including nonstandard Aib at position 2; "
                    "lysine 20 carries a linker and C18 fatty diacid. "
                    "Not supported by the standard-amino-acid sequence builder."
                ),
                "source_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/215256s024lbl.pdf",
            },
            "tirzepatide": {
                "name": "Tirzepatide",
                "effect": "A dual GIP/GLP-1 receptor agonist involved in regulating insulin secretion and appetite.",
                "structure_notes": (
                    "39 residues, including nonstandard Aib at positions 2 and 13; "
                    "lysine 20 carries a linker and C20 fatty diacid, and the "
                    "C-terminus is amidated. Not supported by the "
                    "standard-amino-acid sequence builder."
                ),
                "source_url": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/217806Orig1s000PharmR.pdf",
            },
        }

    def lookup(self, peptide: Peptide) -> dict[str, str] | None:
        """Return a reference record for an exact full sequence, or None.

        An absent sequence means only that it is absent from this small table.
        A sequence match does not confirm the molecule's biological effects.
        """
        record = self.peptides.get(peptide.sequence)
        return record.copy() if record is not None else None

    def show_options(self) -> None:
        """Print the example sequences and their documented biological roles."""
        print("\nKnown peptide references (sequence matches only):")
        for sequence, record in self.peptides.items():
            print(f"  {record['name']} | {sequence} | {record['effect']}")
        print("\nName-only references (require nonstandard residues):")
        for record in self.name_only_peptides.values():
            print(f"  {record['name']} | {record['effect']}")

    def lookup_name(self, name: str) -> dict[str, str] | None:
        """Find peptide information by name without identifying an input chain."""
        name = name.strip().casefold()
        for sequence, record in self.peptides.items():
            if record["name"].casefold() == name:
                return {**record, "sequence": sequence}
        record = self.name_only_peptides.get(name)
        return record.copy() if record is not None else None

# define more classes
