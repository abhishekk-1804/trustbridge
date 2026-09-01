import { create } from 'zustand';

interface State {
  count: number;
  inc: () => void;
}

const useStore = create<{ count: number; inc: () => void }>((set) => ({
  count: 0,
  inc: () => set((state) => ({ count: state.count + 1 })),
}));
