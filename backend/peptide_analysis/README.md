# PepperQ sequence-derived peptide analysis

This isolated package turns an imported, standard amino-acid primary sequence into
transparent **calculated descriptors**. It does not supply experimentally measured
properties or claim peptide compatibility, biological activity, safety, affinity,
synergy, solubility, aggregation resistance, or clinical relevance.

## Supported input and assumptions

- Standard one-letter amino-acid sequences only: A, C, D, E, F, G, H, I, K, L,
  M, N, P, Q, R, S, T, V, W, and Y.
- A linear, unmodified peptide with free amino and carboxyl termini.
- A target pH from 0 through 14 for the net-charge estimate.
- Biopython is the calculation library. Results should record the installed
  Biopython version in any reproducible workflow.

The package withholds sequence-derived chemistry values when a sequence is missing,
contains an unsupported residue, declares any modification, has a non-free terminal
chemistry, or is marked nonselectable by the peptide library. It never silently
substitutes an unmodified free-terminal model for a modified peptide.

## Descriptor methods

| Field | Method and unit |
| --- | --- |
| Molecular mass | Bio.SeqUtils.molecular_weight with protein sequence type and average mass: Da for the stated linear free-terminus model. |
| Net charge | Bio.SeqUtils.ProtParam.ProteinAnalysis.charge_at_pH, using Biopython's Bjellqvist pKa model. Estimated, not measured. |
| Isoelectric point | ProteinAnalysis.isoelectric_point, using Biopython's Bjellqvist pKa model. Estimated, not measured. |
| Hydropathy | ProteinAnalysis.gravy, the Kyte-Doolittle average hydropathy. |
| Residue composition | Direct counts of the submitted standard one-letter sequence. Basic composition is K/R/H; acidic composition is D/E. |
| Pair terms | Normalized Levenshtein edit similarity/diversity plus absolute differences in calculated hydropathy and pH-specific net charge. These are string/descriptor proxies, not interaction predictions. |

## Read-only peptide-library boundary

analyze_library_peptide(lookup, peptide_id) requires an injected object exposing
only get(peptide_id). It does not instantiate a library service, initialize a
database, import data, update a record, or call an upsert operation. The adapter
inspects primarySource.modifications, sourceReferences[].modifications,
nonstandardResidues, and selectableForOptimization before calculating.

For already retrieved library mappings, analyze_library_records accepts a bounded
batch without touching the library. It converts source-declared modifications,
nonstandard-residue flags, and nonselectable flags into explicit calculation
limitations rather than treating the submitted one-letter sequence as an
unmodified experimental sample.

## Initial eight-candidate experiment

Use CandidateRecord and analyze_candidate_set with require_exactly_eight set to
true. For eight valid records, the returned object contains eight individual
analyses and 28 unordered pairwise proxy terms. The helper intentionally limits the
default set to eight records for the initial small QUBO experiment; it has no QUBO
or QAOA code.

## Researcher-defined score exchange

ResearchGoal requires all of the following:

1. A metric name.
2. A direction: maximize, minimize, or target.
3. A positive weight.
4. Explicit lower and upper normalization bounds.
5. A target value when applicable.

score_sequence, score_pair, and build_qubo_scoring_contract do not create default
goals, weights, or penalties. A downstream quantum-optimization owner must agree
with the chemistry researcher on how the returned normalized scores map to a QUBO
reward or pair term, including the sign, scaling, blend-size constraint, and
interpretation.

## Reproduction

From the repository root, install this isolated dependency and run its focused
tests:

    python -m pip install -r backend/peptide_analysis/requirements.txt
    python -m pytest backend/peptide_analysis/test_peptide_analysis.py -q -p no:cacheprovider


