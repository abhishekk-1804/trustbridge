import * as React from 'react';
import { cn } from '@/utils';

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function ScrollArea({ className, children, ...props }: ScrollAreaProps) {
  return (
    <div
      className={cn('overflow-y-auto scrollbar-thin', className)}
      {...props}
    >
      {children}
    </div>
  );
}