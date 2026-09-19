import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (item: T, index: number) => ReactNode;
  className?: string;
  headerClassName?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  emptyMessage?: ReactNode;
  className?: string;
  keyExtractor?: (item: T) => string;
}

export function Table<T>({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No records found',
  className = '',
  keyExtractor
}: TableProps<T>) {
  return (
    <div className={`border border-border rounded-xl overflow-hidden bg-surface ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border bg-surface2/90 sticky top-0 z-10 backdrop-blur-sm">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`py-3.5 px-4 font-mono text-[11px] uppercase tracking-[0.18em] text-muted font-semibold ${
                    col.headerClassName || ''
                  }`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-12 text-center text-muted font-sans">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item, idx) => (
                <tr
                  key={keyExtractor ? keyExtractor(item) : idx}
                  onClick={() => onRowClick && onRowClick(item)}
                  className={`transition-colors ${
                    idx % 2 === 1 ? 'bg-surface2/30' : 'bg-surface'
                  } ${
                    onRowClick
                      ? 'cursor-pointer hover:bg-surface2 hover:border-b-border2'
                      : ''
                  }`}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={`py-3.5 px-4 text-sm ${col.className || ''}`}>
                      {col.render(item, idx)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
