import * as React from 'react';
import { cn } from '@/utils';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T, index: number) => React.ReactNode;
  className?: string;
  headerClassName?: string;
}

export interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyField: string;
  emptyMessage?: string;
  striped?: boolean;
  hoverable?: boolean;
  className?: string;
}

export function Table<T extends { [key: string]: any }>({
  data,
  columns,
  keyField,
  emptyMessage = 'No data available',
  striped = true,
  hoverable = true,
  className,
}: TableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="table-container">
        <div className="card">
          <div className="px-6 py-12 text-center">
            <p className="text-text-muted">{emptyMessage}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('table-container', className)}>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    column.headerClassName,
                    column.className
                  )}
                  style={{ width: column.className?.includes('w-') ? undefined : 'auto' }}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={row[keyField]} className={cn(striped && rowIndex % 2 === 1 && 'bg-bg-elevated', hoverable && 'hover:bg-bg-elevated')}>
                {columns.map((column) => (
                  <td key={column.key} className={cn(column.className)}>
                    {column.render ? column.render(row, rowIndex) : (row[column.key] as React.ReactNode)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}