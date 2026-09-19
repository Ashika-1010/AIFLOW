import React, { createContext, useContext, useState, type ReactNode } from 'react';
import type { Region, Receipt } from '../mock/types';
import { DEFAULT_REGION } from '../mock/regions';
import { MOCK_RECEIPTS } from '../mock/data';

export interface SessionStats {
  requests: number;
  llmCallsAvoided: number;
  estEnergySavedWh: number;
}

interface AppContextType {
  region: Region;
  setRegion: (region: Region) => void;
  qualityFloor: number;
  setQualityFloor: (quality: number) => void;
  pessimistic: boolean;
  setPessimistic: (pessimistic: boolean) => void;
  togglePessimistic: () => void;
  sessionStats: SessionStats;
  recordSessionRequest: (receipt: Receipt) => void;
  receipts: Receipt[];
  methodologyModalOpen: boolean;
  setMethodologyModalOpen: (open: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [region, setRegion] = useState<Region>(DEFAULT_REGION);
  const [qualityFloor, setQualityFloor] = useState<number>(0.60);
  const [pessimistic, setPessimistic] = useState<boolean>(false);
  const [methodologyModalOpen, setMethodologyModalOpen] = useState<boolean>(false);
  const [receipts, setReceipts] = useState<Receipt[]>(MOCK_RECEIPTS);

  const [sessionStats, setSessionStats] = useState<SessionStats>({
    requests: 0,
    llmCallsAvoided: 0,
    estEnergySavedWh: 0
  });

  const togglePessimistic = () => {
    setPessimistic(prev => !prev);
  };

  const recordSessionRequest = (receipt: Receipt) => {
    // Add to receipts state
    setReceipts(prev => [receipt, ...prev]);

    // Check if LLM call was avoided (Tier 0, 0.5, or 1)
    const isAvoided = receipt.pathway === 'deterministic' || receipt.pathway === 'cache' || receipt.pathway === 'retrieval';
    const energySaved = Math.max(0, receipt.baselineEnergyWh - receipt.energyWh.central);

    setSessionStats(prev => ({
      requests: prev.requests + 1,
      llmCallsAvoided: prev.llmCallsAvoided + (isAvoided ? 1 : 0),
      estEnergySavedWh: +(prev.estEnergySavedWh + energySaved).toFixed(4)
    }));
  };

  return (
    <AppContext.Provider
      value={{
        region,
        setRegion,
        qualityFloor,
        setQualityFloor,
        pessimistic,
        setPessimistic,
        togglePessimistic,
        sessionStats,
        recordSessionRequest,
        receipts,
        methodologyModalOpen,
        setMethodologyModalOpen
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export function useApp(): AppContextType {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
