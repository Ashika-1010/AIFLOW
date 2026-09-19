import React from 'react';

interface ExampleChipsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}

export const EXAMPLE_PROMPTS = [
  'What is 27 × 43?',
  'Rewrite this paragraph professionally',
  'Explain quantum entanglement simply',
  'Analyze this technical document'
];

export const ExampleChips: React.FC<ExampleChipsProps> = ({ onSelect, disabled = false }) => {
  return (
    <div className="flex flex-wrap gap-2.5">
      {EXAMPLE_PROMPTS.map((prompt) => (
        <button
          key={prompt}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(prompt)}
          className="text-xs font-mono px-3 py-1.5 rounded-lg border border-border bg-surface2/60 text-muted hover:border-border2 hover:text-text hover:bg-surface2 transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
};
