import type { Region } from './types';

export const MOCK_REGIONS: Region[] = [
  { id: 'IN', label: 'India',   gridIntensity: 713 },
  { id: 'DE', label: 'Germany', gridIntensity: 344 },
  { id: 'US', label: 'USA',     gridIntensity: 369 },
  { id: 'FR', label: 'France',  gridIntensity:  56 },
  { id: 'SE', label: 'Sweden',  gridIntensity:  41 }
];

export const DEFAULT_REGION = MOCK_REGIONS[0]; // India (713 gCO2e/kWh)
