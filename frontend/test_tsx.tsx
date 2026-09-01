
import React from 'react';

interface Event {
  id: number;
  user_name: string;
  reason: string;
  timestamp: string;
}

interface Props {
  events: Event[];
  loading: boolean;
}

export function TestComponent({ events, loading }: Props) {
  return (
    <div>
      {loading ? (
        [1, 2, 3].map((i) => <div key={i} className='h-16 animate-pulse bg-gray-100 rounded' />)
      ) : (
        events.slice(0, 5).map((event) => (
          <div key={event.id} className='flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200'>
            <div className='w-2 h-2 rounded-full bg-red-400' />
            <div className='flex-1 min-w-0'>
              <p className='text-sm font-medium text-gray-900 truncate'>{event.user_name}</p>
              <p className='text-xs text-gray-500 truncate'>{event.reason}</p>
            </div>
            <div className='text-right'>
              <span className='inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800'>HIGH</span>
              <p className='text-xs text-gray-500 mt-0.5'>{event.timestamp}</p>
            </div>
          </div>
        ))}
      )}
    </div>
  );
}
