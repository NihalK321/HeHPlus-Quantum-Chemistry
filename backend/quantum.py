"""Qiskit encoding for a small, explicitly enumerated energy landscape.

An arbitrary energy table can contain higher-order interactions. We use its
exact diagonal cost unitary; we do not assume it is a quadratic QUBO. Building
the table and circuit this way costs exponentially many resources, so this is
a benchmark experiment and carries no quantum speedup claim.
"""

import sys

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import DiagonalGate
from qiskit.quantum_info import SparsePauliOp, Statevector


def validate_energies(energies) -> np.ndarray:
    values = np.asarray(energies, dtype=float)
    if values.ndim != 1 or len(values) < 2 or len(values) & (len(values) - 1):
        raise ValueError("Energy table must have a power-of-two length of at least two.")
    if len(values) > 32 or not np.all(np.isfinite(values)):
        raise ValueError("Use at most 32 finite configuration energies.")
    return values


def cost_hamiltonian(energies) -> SparsePauliOp:
    """Return the exact energy diagonal as a sum of I/Z Pauli strings.

    Basis index i corresponds to format(i, '0nb'), following Qiskit bit order.
    """
    values = validate_energies(energies)
    n = len(values).bit_length() - 1
    terms = []
    for mask in range(len(values)):
        coefficient = sum(
            energy * (-1 if (index & mask).bit_count() % 2 else 1)
            for index, energy in enumerate(values)
        ) / len(values)
        label = "".join("Z" if mask & (1 << qubit) else "I" for qubit in reversed(range(n)))
        terms.append((label, coefficient))
    return SparsePauliOp.from_list(terms)


def build_qaoa_circuit(energies, parameters) -> QuantumCircuit:
    """Parameters are [gamma_0, beta_0, gamma_1, beta_1, ...]."""
    values = validate_energies(energies)
    parameters = np.asarray(parameters, dtype=float)
    if parameters.ndim != 1 or len(parameters) == 0 or len(parameters) % 2 or not np.all(np.isfinite(parameters)):
        raise ValueError("Supply finite gamma/beta pairs.")
    spread = float(np.ptp(values))
    scaled = (values - values.min()) / spread if spread > 0 else np.zeros_like(values)
    n = len(values).bit_length() - 1
    circuit = QuantumCircuit(n)
    circuit.h(range(n))
    for gamma, beta in parameters.reshape(-1, 2):
        circuit.append(DiagonalGate(np.exp(-1j * gamma * scaled)), list(range(n)))
        for qubit in range(n):
            circuit.rx(2 * beta, qubit)
    return circuit


def qaoa_probabilities(energies, parameters) -> np.ndarray:
    """Evaluate an ideal statevector circuit; no hardware account is needed."""
    return Statevector.from_instruction(build_qaoa_circuit(energies, parameters)).probabilities()


def _expand_for_display(circuit: QuantumCircuit) -> QuantumCircuit:
    """Expand gate definitions without loading hardware transpiler plugins."""
    expanded = QuantumCircuit(circuit.num_qubits)

    def append_definition(definition, wires):
        expanded.global_phase += definition.global_phase
        for instruction in definition.data:
            mapped = [wires[definition.find_bit(qubit).index] for qubit in instruction.qubits]
            if instruction.operation.name in {"h", "rz", "rx", "cx"}:
                expanded.append(instruction.operation, mapped)
            else:
                append_definition(instruction.operation.definition, mapped)

    append_definition(circuit, list(range(circuit.num_qubits)))
    return expanded


def _console_diagram(circuit: QuantumCircuit) -> str:
    drawing = circuit.draw(output="text", fold=110)
    drawing.encoding = "utf-8"
    # ASCII wires remain readable in Windows terminals using legacy encodings.
    translation = {ord(character): "+" for character in "┌┐└┘┬┴├┤┼╫╪╡╞╤╧╥╨"}
    translation.update(str.maketrans({"─": "-", "═": "=", "│": "|", "║": "|", "■": "o", "░": "|"}))
    return str(drawing).translate(translation)


def print_qaoa_circuit(energies, parameters, sequence: str, torsion_names: list[str]) -> None:
    """Print the final circuit once, including an equivalent expanded view.

    This is a display helper, separate from circuit evaluations during fitting.
    The expanded view exposes the diagonal phase gate as RZ/CX operations.
    """
    circuit = build_qaoa_circuit(energies, parameters)
    expanded = _expand_for_display(circuit)
    lines = [f"\nFinal QAOA circuit for {sequence}",
             "Ideal statevector simulation; no hardware measurements are included."]
    for qubit, name in enumerate(torsion_names):
        lines.append(f"  q_{qubit}: {name} (0 = angle option 0; 1 = angle option 1)")
    for layer, (gamma, beta) in enumerate(np.asarray(parameters).reshape(-1, 2), start=1):
        lines.append(f"  Layer {layer}: gamma={gamma:.6f}, beta={beta:.6f} radians")
    lines.extend([
        "\nCircuit overview (Diagonal = energy-dependent cost phase):",
        _console_diagram(circuit),
        "\nEquivalent circuit expanded into H, RZ, RX, and CX gates:",
        _console_diagram(expanded),
        "H prepares superposition; RZ/CX encode the cost; RX provides mixing.",
        "Probabilities are calculated from the statevector; counts are sampled afterward.\n",
    ])
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print("\n".join(lines).encode(encoding, errors="replace").decode(encoding), flush=True)
