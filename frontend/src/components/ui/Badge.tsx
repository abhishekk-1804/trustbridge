import * as React from 'react';
import { cn } from '@/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'neutral', children, ...props }, ref) => {
    const variants = {
      success: 'badge badge-success',
      warning: 'badge badge-warning',
      danger: 'badge badge-danger',
      info: 'badge badge-info',
      neutral: 'badge badge-neutral',
    };

    return (
      <span
        ref={ref}
        className={cn(variants[variant], className)}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export { Badge };