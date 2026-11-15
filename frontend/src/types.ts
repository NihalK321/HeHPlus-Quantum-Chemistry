export interface CalculationConfig {
  basis: string
  bond_distance_angstrom: number
  charge: number
  ftol: number
  maxiter: number
  spin: number
}

export interface EnergyPoint {
  absolute_electronic_error_hartree: number
  absolute_total_energy_error_hartree: number
  ansatz: string
  calculated_with: string
  calculation_status: string
  circuit_depth: number
  circuit_text: string
  classical_electronic_energy_hartree: number
  classical_reference_method: string
  classical_total_molecular_energy_hartree: number
  config: CalculationConfig
  decomposed_circuit_depth: number
  electron_count: number
  electronic_energy_hartree: number
  energy_convention: string
  estimator: string
  limitations: string[]
  mapping: string
  molecule: string
  nuclear_repulsion_hartree: number
  optimal_parameters: number[]
  optimizer: string
  optimizer_evaluations: number
  package_versions: Record<string, string>
  parameter_count: number
  qubit_count: number
  total_molecular_energy_hartree: number
}

export interface ScanDocument {
  created_at_utc: string
  energy_convention: string
  molecule: string
  result_source: string
  results: EnergyPoint[]
}

export interface HardwarePreflight {
  ansatz: string
  backend_name: string | null
  basis: string
  bond_distance_angstrom: number
  created_at_utc: string
  electron_count: number
  energy_convention: string
  exact_classical_total_energy_hartree: number
  execution_status: string
  hardware_execution: boolean
  job_id: string | null
  local_ideal_vqe_total_energy_hartree: number
  local_vqe_vs_classical_absolute_error_hartree: number
  logical_qubit_count: number
  mapping: string
  measured_electronic_energy_hartree?: number | null
  measured_electronic_energy_stddev_hartree?: number | null
  measured_total_energy_hartree?: number | null
  molecular_charge: number
  molecule: string
  nuclear_repulsion_hartree: number
  observable_layout_step: string
  requested_estimator_options: {
    default_shots: number | null
    mitigation_note: string
    precision: number | null
    resilience_level: number | null
  }
  submission_safety: string
  variational_parameter_count: number
}
