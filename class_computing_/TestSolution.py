from classic_computing_solution import AMINO_ACIDS, Peptide, PeptideTable


def test_peptide():
    peptide = Peptide()

    # Add amino-acid names and verify that their order is preserved.
    peptide.add_amino_acid("alanine")
    peptide.add_amino_acid("glycine")
    peptide.add_amino_acid("serine")

    assert peptide.amino_acids == ["alanine", "glycine", "serine"]
    assert len(peptide) == 3
    print("Amino-acid names:", peptide.amino_acids)

    # A second peptide can store single-letter codes independently.
    another_peptide = Peptide()
    another_peptide.add_amino_acid("A")
    another_peptide.add_amino_acid("G")
    another_peptide.add_amino_acid(" S ")

    assert another_peptide.amino_acids == ["A", "G", "S"]
    assert len(another_peptide) == 3
    assert peptide.amino_acids == ["alanine", "glycine", "serine"]
    print("Amino-acid codes:", another_peptide.amino_acids)
    print("All peptide tests passed!")


def test_peptide_table():
    table = PeptideTable()
    for sequence, reference in table.peptides.items():
        peptide = Peptide()
        for code in sequence:
            peptide.add_amino_acid(code)
        assert table.lookup(peptide)["name"] == reference["name"]

    # Names and three-letter codes must match the same complete sequence.
    peptide = Peptide()
    for amino_acid in ("tyrosine", "Gly", " g ", "phenylalanine", "Met"):
        peptide.add_amino_acid(amino_acid)
    assert peptide.sequence == "YGGFM"
    assert table.lookup(peptide)["name"] == "Met-enkephalin"

    # A partial sequence, changed order, or longer sequence is not a match.
    for sequence in ("", "Y", "YGGF", "YFGGM", "AYGGFM", "AGS"):
        peptide = Peptide()
        for code in sequence:
            peptide.add_amino_acid(code)
        assert table.lookup(peptide) is None

    assert len(AMINO_ACIDS) == 20
    for name in ("Carnosine", "Semaglutide", "Tirzepatide", "Liraglutide", "Exenatide", "Tesamorelin"):
        assert table.lookup_name(name)["name"] == name
    assert table.lookup_name("  SEMAGLUTIDE ")["name"] == "Semaglutide"
    assert table.lookup_name("unknown peptide") is None
    # Standard alanine must not be mistaken for beta-alanine or Aib.
    for sequence in ("AH", "HAEGTFTSDVSSYLEGQAAKEFIAWLVRGRG"):
        peptide = Peptide()
        for code in sequence:
            peptide.add_amino_acid(code)
        match = table.lookup(peptide)
        assert match is None or match["name"] == "Liraglutide"
    print("All peptide reference tests passed!")


def build_peptide():
    """Let the user build a sequence from the 20 standard amino acids."""
    peptide = Peptide()
    table = PeptideTable()
    choices = {}
    for code, (name, abbreviation) in AMINO_ACIDS.items():
        for label in (code, name, abbreviation):
            choices[label.casefold()] = code

    def show_options():
        print("\nThe 20 standard amino acids:")
        for code, (name, abbreviation) in AMINO_ACIDS.items():
            print(f"  {code}  {abbreviation:3}  {name}")

    show_options()
    print("\nEnter one amino acid at a time by name or code (for example, alanine, Ala, or A).")
    print("Enter 'options' for amino acids, 'peptides' for known peptide examples, or 'done' to finish.")
    print("Enter 'info <peptide name>' to read a reference, for example 'info semaglutide'.")

    while True:
        try:
            entry = input("Add amino acid: ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if entry == "done":
            break
        if entry == "options":
            show_options()
            continue
        if entry == "peptides":
            table.show_options()
            continue
        if entry.startswith("info "):
            reference = table.lookup_name(entry[5:])
            if reference is None:
                print("No peptide with that name in this small reference table.")
            else:
                print("\nPeptide:", reference["name"])
                print("Sequence:", reference.get("sequence", "Requires residues outside the standard 20."))
                print("Biological role:", reference["effect"])
                print("Structure:", reference["structure_notes"])
                for key in ("source_url", "effect_source_url", "sequence_source_url"):
                    if key in reference:
                        print("Source:", reference[key])
            continue

        code = choices.get(entry)
        if code is None:
            print("Unrecognized amino acid. Enter a listed name or code, or 'options'.")
            continue

        peptide.add_amino_acid(code)
        print(f"Added {AMINO_ACIDS[code][0]}. Sequence: {'-'.join(peptide.amino_acids)}")

    print("\nFinal sequence (N- to C-terminus):", "-".join(peptide.amino_acids) or "(empty)")
    print("Number of amino acids:", len(peptide))
    reference = table.lookup(peptide)
    if reference is None:
        print("No exact sequence match in this small reference table.")
        print("This does not mean the peptide has no biological activity.")
    else:
        print("\nExact backbone sequence match to reference:", reference["name"])
        print("Documented role of the reference peptide:", reference["effect"])
        print("Reference structure:", reference["structure_notes"])
        print("Source:", reference["source_url"])
        if "effect_source_url" in reference:
            print("Role source:", reference["effect_source_url"])
        if "sequence_source_url" in reference:
            print("Sequence source:", reference["sequence_source_url"])
        print("This lookup checks sequence only; it does not verify structure or predict activity.")
    return peptide


if __name__ == "__main__":
    build_peptide()
