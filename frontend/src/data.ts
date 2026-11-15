import type { HardwarePreflight, ScanDocument } from './types'

const baseUrl = import.meta.env.BASE_URL

export const artifactUrl = (file: string) => `${baseUrl}${file}`

async function getArtifact<T>(file: string): Promise<T> {
  const response = await fetch(artifactUrl(file), { cache: 'no-cache' })
  if (!response.ok) {
    throw new Error(`Could not load ${file} (HTTP ${response.status}).`)
  }
  return (await response.json()) as T
}

function validateScan(scan: ScanDocument): ScanDocument {
  if (scan.molecule !== 'HeH+' || !Array.isArray(scan.results) || scan.results.length === 0) {
    throw new Error('The potential-energy scan is not a valid verified HeH+ result artifact.')
  }

  if (
    scan.results.some(
      (point) =>
        !Number.isFinite(point.config?.bond_distance_angstrom) ||
        !Number.isFinite(point.total_molecular_energy_hartree) ||
        !Number.isFinite(point.classical_total_molecular_energy_hartree),
    )
  ) {
    throw new Error('The potential-energy scan contains incomplete energy points.')
  }

  return scan
}

function validateHardware(record: HardwarePreflight): HardwarePreflight {
  if (record.molecule !== 'HeH+' || typeof record.hardware_execution !== 'boolean') {
    throw new Error('The hardware preflight record has an unsupported shape.')
  }
  return record
}

export async function loadChallengeArtifacts(): Promise<{
  scan: ScanDocument
  hardware: HardwarePreflight
}> {
  const [rawScan, rawHardware] = await Promise.all([
    getArtifact<ScanDocument>('hehplus_potential_energy_scan.json'),
    getArtifact<HardwarePreflight>('hardware/hehplus_hardware_preflight.json'),
  ])

  return {
    scan: validateScan(rawScan),
    hardware: validateHardware(rawHardware),
  }
}
