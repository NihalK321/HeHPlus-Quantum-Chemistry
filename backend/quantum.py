"""Build and simulate QAOA circuits for the peptide bond-angle experiment.

Suggested reading order:
    1. validate_energies()    - check the input energy table
    2. build_qaoa_circuit()  - build the circuit, step by step
    3. qaoa_probabilities()  - calculate outcome probabilities

Each bit chooses one of two allowed angles for a selected bond. The energies
come from a classical chemistry calculation, not from this quantum circuit.
For two qubits, energies are ordered [E(00), E(01), E(10), E(11)]. The rightmost
bit is qubit 0. With three qubits, there are eight entries, and so on.

The remaining functions describe the energy operator or print the circuit.
They are useful, but can be read after the three functions listed above.

We use an exact diagonal cost gate, which can represent higher-order terms,
rather than assuming the energy model is a quadratic QUBO. Enumerating the
table costs exponentially many resources. This ideal-simulator experiment
does not demonstrate quantum speedup or predict peptide activity.
The original implementation is preserved in quantum_reference.py.
"""

import sys
from itertools import product
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import DiagonalGate
from qiskit.quantum_info import SparsePauliOp, Statevector


def validate_energies(energies) -> np.ndarray:
    """Require one finite energy per possible outcome, for at most 5 qubits.

    One qubit needs 2 energies, two qubits need 4, three need 8, and so on.
    """
    energy_values = np.asarray(energies, dtype=float)

    # A one-dimensional array is a simple list, not a table of lists.
    if energy_values.ndim != 1:
        raise ValueError("Energy table must have a power-of-two length of at least two.")

    number_of_energies = len(energy_values)
    if number_of_energies < 2:
        raise ValueError("Energy table must have a power-of-two length of at least two.")

    # bit_length() - 1 gives log2(size), rounded down, using integer arithmetic.
    number_of_qubits = number_of_energies.bit_length() - 1
    if 2 ** number_of_qubits != number_of_energies:
        raise ValueError("Energy table must have a power-of-two length of at least two.")

    if number_of_energies > 32 or not np.all(np.isfinite(energy_values)):
        raise ValueError("Use at most 32 finite configuration energies.")

    return energy_values


def cost_hamiltonian(energies) -> SparsePauliOp:
    """ADVANCED: Express the energy table as a sum of I/Z Pauli operators.

    A Hamiltonian here assigns an energy to each bitstring. I contributes +1
    for either bit; Z contributes +1 for bit 0 and -1 for bit 1. Weighted
    combinations such as IZ, ZI, and ZZ can reproduce the energy table.

    The circuit builder below uses DiagonalGate directly. It does NOT call
    this alternative representation. Skip this function on your first read.
    """
    energy_values = validate_energies(energies)
    number_of_configurations = len(energy_values)
    number_of_qubits = number_of_configurations.bit_length() - 1
    pauli_terms = []

    # For two qubits this produces II, IZ, ZI, ZZ, in that order.
    for operator_letters in product("IZ", repeat=number_of_qubits):
        operator_label = "".join(operator_letters)
        signed_energy_sum = 0.0

        for configuration_index, energy in enumerate(energy_values):
            bitstring = format(configuration_index, f"0{number_of_qubits}b")
            sign = 1

            # Both strings put the highest-numbered qubit on the left.
            for operator_letter, bit in zip(operator_label, bitstring):
                if operator_letter == "Z" and bit == "1":
                    sign = -sign

            signed_energy_sum += sign * energy

        coefficient = signed_energy_sum / number_of_configurations
        pauli_terms.append((operator_label, coefficient))

    return SparsePauliOp.from_list(pauli_terms)


def build_qaoa_circuit(energies, parameters) -> QuantumCircuit:
    """Build a fresh circuit using the supplied gamma/beta settings.

    One layer uses [gamma, beta]. Two layers use:
        [gamma_0, beta_0, gamma_1, beta_1]

    Gamma controls the energy-dependent phase changes. Beta controls mixing.
    This function does not search for good settings; optimizer.py does that.
    """
    # STEP 1: Check the energy table and the gamma/beta parameter pairs.
    energy_values = validate_energies(energies)
    parameter_values = np.asarray(parameters, dtype=float)

    if parameter_values.ndim != 1:
        raise ValueError("Supply finite gamma/beta pairs.")
    if len(parameter_values) == 0 or len(parameter_values) % 2 != 0:
        raise ValueError("Supply finite gamma/beta pairs.")
    if not np.all(np.isfinite(parameter_values)):
        raise ValueError("Supply finite gamma/beta pairs.")

    # STEP 2: Scale energies to [0, 1], preserving their ordering.
    # NumPy subtracts/divides each array element individually.
    lowest_energy = energy_values.min()
    energy_range = float(np.ptp(energy_values))  # maximum minus minimum

    if energy_range > 0:
        scaled_energies = (energy_values - lowest_energy) / energy_range
    else:
        # Equal energies: use zeros instead of dividing by zero.
        scaled_energies = np.zeros_like(energy_values)

    # STEP 3: Create enough qubits to represent every configuration.
    number_of_configurations = len(energy_values)
    number_of_qubits = number_of_configurations.bit_length() - 1
    circuit = QuantumCircuit(number_of_qubits)

    # STEP 4: Apply H to every qubit. All bitstrings start equally likely.
    for qubit in range(number_of_qubits):
        circuit.h(qubit)

    # STEP 5: Add one cost operation and mixer for each gamma/beta pair.
    for parameter_index in range(0, len(parameter_values), 2):
        gamma = parameter_values[parameter_index]
        beta = parameter_values[parameter_index + 1]

        # COST: Each outcome receives its own phase factor.
        # 1j is Python's imaginary unit. exp(-1j * angle) has magnitude 1:
        # multiplying an amplitude by it rotates the amplitude without changing
        # its magnitude. This operation alone does not change probabilities.
        phase_factors = np.exp(-1j * gamma * scaled_energies)
        cost_gate = DiagonalGate(phase_factors)
        circuit.append(cost_gate, list(range(number_of_qubits)))

        # MIXER: RX mixes amplitude contributions. Their phase differences can
        # now affect probabilities. The angle is 2*beta because Qiskit's RX
        # uses exp(-1j * angle/2 * X). Arbitrary settings need not lower energy.
        for qubit in range(number_of_qubits):
            circuit.rx(2 * beta, qubit)

    return circuit


def qaoa_probabilities(energies, parameters) -> np.ndarray:
    """Simulate the circuit and return probabilities in energy-table order."""
    circuit = build_qaoa_circuit(energies, parameters)

    # Simulate from the all-zero state. The statevector stores complex
    # amplitudes; it is not a collection of quantum hardware measurements.
    final_state = Statevector.from_instruction(circuit)

    # Each probability is abs(amplitude)**2. This calculates the full ideal
    # distribution. optimizer.py separately samples it to produce counts.
    probabilities = final_state.probabilities()
    return probabilities


def _expand_for_display(circuit: QuantumCircuit) -> QuantumCircuit:
    """DISPLAY ONLY: open bundled gates to show an H/RZ/RX/CX circuit.

    Bundled gates can contain other bundled gates. The helper calls itself
    until it reaches the basic gates we want to display (recursion).
    """
    expanded_circuit = QuantumCircuit(circuit.num_qubits)
    basic_gate_names = {"h", "rz", "rx", "cx"}

    def append_definition(definition, destination_qubits):
        # Preserve the global phase when replacing a gate with its definition.
        expanded_circuit.global_phase += definition.global_phase
        for instruction in definition.data:
            mapped_qubits = []
            for qubit in instruction.qubits:
                local_qubit_index = definition.find_bit(qubit).index
                mapped_qubits.append(destination_qubits[local_qubit_index])

            operation = instruction.operation
            if operation.name in basic_gate_names:
                expanded_circuit.append(operation, mapped_qubits)
            else:
                append_definition(operation.definition, mapped_qubits)

    append_definition(circuit, list(range(circuit.num_qubits)))
    return expanded_circuit


def _console_diagram(circuit: QuantumCircuit) -> str:
    """DISPLAY ONLY: make Qiskit's text drawing readable on Windows."""
    drawing = circuit.draw(output="text", fold=110)
    drawing.encoding = "utf-8"
    # ASCII wires remain readable in Windows terminals using legacy encodings.
    translation = {ord(character): "+" for character in "┌┐└┘┬┴├┤┼╫╪╡╞╤╧╥╨"}
    translation.update(str.maketrans({"─": "-", "═": "=", "│": "|", "║": "|", "■": "o", "░": "|"}))
    return str(drawing).translate(translation)


def export_composer_circuit(circuit: QuantumCircuit, filename="quantum_circuit.qasm") -> Path:
    """Save the circuit as OpenQASM 2 for IBM Quantum Composer.

    Expand the bundled cost gate into H/RZ/RX/CX operations so Composer can
    display the individual gates. OpenQASM 2 omits global phase, which does
    not affect this circuit's outcome probabilities. Parameters are the fitted
    numerical values for this run; this file does not contain the optimizer.
    """
    expanded_circuit = _expand_for_display(circuit)
    output_path = Path(filename).resolve()
    qasm2.dump(expanded_circuit, output_path)
    return output_path


def print_qaoa_circuit(energies, parameters, sequence: str, torsion_names: list[str]) -> None:
    """DISPLAY ONLY: print the fitted parameters and two circuit views.

    optimizer.py calls this once after fitting, not on every evaluation.
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
    output_text = "\n".join(lines)
    safe_output_text = output_text.encode(encoding, errors="replace").decode(encoding)
    print(safe_output_text, flush=True)

    # Write the same fitted circuit for opening in IBM Quantum Composer.
    # Do this before image rendering so QASM export does not require Matplotlib.
    composer_path = export_composer_circuit(circuit)
    print(f"Saved IBM Composer circuit: {composer_path}", flush=True)

    import matplotlib.pyplot as plt

    figure = circuit.draw(output="mpl", fold=-1)
    figure.savefig("quantum_circuit.png", dpi=300, bbox_inches="tight")
    plt.close(figure)

    # Export the same fitted circuit with the bundled cost gate opened up.
    expanded_figure = expanded.draw(output="mpl", fold=-1)
    expanded_figure.savefig("quantum_circuit_expanded.png", dpi=300, bbox_inches="tight")
    plt.close(expanded_figure)
