export function TestComponent({ events, loading }: { events: any[]; loading: boolean }) {
  return (
    <div>
      {loading ? (
        [1, 2, 3].map((i) => <div key={i} className='h-16' />)
      ) : (
        events.slice(0, 5).map((event) => (
          <div key={event.id} className='flex'>
            <div className='w-2 h-2' />
            <div className='flex-1'>
              <p>{event.user_name}</p>
              <p>{event.reason}</p>
            </div>
            <div className='text-right'>
              <span className='text-red-500'>HIGH</span>
              <p>{event.timestamp}</p>
            </div>
          </div>
        ))}
      )}
    </div>
  );
}
