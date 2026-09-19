import type { Pathway } from '../mock/types';

export interface PathwayConfig {
  label: string;
  badgeLabel: string;
  color: string;
  textColor: string;
  borderColor: string;
  bgTint: string;
  pillBg: string;
}

export const PATHWAY_CONFIGS: Record<Pathway, PathwayConfig> = {
  deterministic: {
    label: 'Deterministic Tool',
    badgeLabel: 'DETERMINISTIC',
    color: '#22C55E',
    textColor: 'text-deterministic',
    borderColor: 'border-deterministic/30',
    bgTint: 'bg-deterministic/10',
    pillBg: 'bg-deterministic/20 text-deterministic border-deterministic/40'
  },
  cache: {
    label: 'Cache Hit',
    badgeLabel: 'CACHE HIT',
    color: '#A855F7',
    textColor: 'text-cache',
    borderColor: 'border-cache/30',
    bgTint: 'bg-cache/10',
    pillBg: 'bg-cache/20 text-cache border-cache/40'
  },
  retrieval: {
    label: 'Retrieval (RAG)',
    badgeLabel: 'RETRIEVAL',
    color: '#6366F1',
    textColor: 'text-retrieval',
    borderColor: 'border-retrieval/30',
    bgTint: 'bg-retrieval/10',
    pillBg: 'bg-retrieval/20 text-retrieval border-retrieval/40'
  },
  small_model: {
    label: 'Small Model (8B)',
    badgeLabel: 'SMALL MODEL',
    color: '#FF2D78',
    textColor: 'text-smallModel',
    borderColor: 'border-smallModel/30',
    bgTint: 'bg-smallModel/10',
    pillBg: 'bg-smallModel/20 text-smallModel border-smallModel/40'
  },
  large_model: {
    label: 'Large Model (70B+)',
    badgeLabel: 'LARGE MODEL',
    color: '#F59E0B',
    textColor: 'text-largeModel',
    borderColor: 'border-largeModel/30',
    bgTint: 'bg-largeModel/10',
    pillBg: 'bg-largeModel/20 text-largeModel border-largeModel/40'
  },
  escalated: {
    label: 'Escalated to Large',
    badgeLabel: 'ESCALATED',
    color: '#EF4444',
    textColor: 'text-escalated',
    borderColor: 'border-escalated/30',
    bgTint: 'bg-escalated/10',
    pillBg: 'bg-escalated/20 text-escalated border-escalated/40'
  }
};

export function getPathwayConfig(pathway: Pathway): PathwayConfig {
  return PATHWAY_CONFIGS[pathway] || PATHWAY_CONFIGS.small_model;
}
