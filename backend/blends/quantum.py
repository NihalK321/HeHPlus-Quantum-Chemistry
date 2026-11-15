"""Whole-peptide QUBO -> Ising -> native RZ/RZZ/RX QAOA, for up to 8 qubits.

This is separate from backend.quantum, whose bits choose molecular bond angles.
Here bit i means 'include candidate i'; the rightmost displayed bit is bit 0.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def qubo_to_ising(constant, linear, quadratic):
    """Substitute x_i=(1-Z_i)/2; quadratic contains each i<j term once."""
    fields = -np.asarray(linear, dtype=float) / 2
    couplings = np.asarray(quadratic, dtype=float) / 4
    offset = constant + sum(linear) / 2 + np.sum(quadratic) / 4
    for first in range(len(fields)):
        for second in range(first + 1, len(fields)):
            fields[first] -= quadratic[first, second] / 4
            fields[second] -= quadratic[first, second] / 4
    return float(offset), fields, couplings


def build_blend_circuit(fields, couplings, parameters, energy_scale):
    circuit = QuantumCircuit(len(fields))
    circuit.h(range(len(fields)))
    for gamma, beta in np.asarray(parameters).reshape(-1, 2):
        for index, coefficient in enumerate(fields):
            circuit.rz(2 * gamma * coefficient / energy_scale, index)
        for first in range(len(fields)):
            for second in range(first + 1, len(fields)):
                circuit.rzz(2 * gamma * couplings[first, second] / energy_scale, first, second)
        for index in range(len(fields)):
            circuit.rx(2 * beta, index)
    return circuit


def probabilities(fields, couplings, parameters, energy_scale):
    circuit = build_blend_circuit(fields, couplings, parameters, energy_scale)
    return Statevector.from_instruction(circuit).probabilities()
