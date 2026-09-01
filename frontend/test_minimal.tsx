
const useToastStore = create<ToastState>((set) => {
  return {
    toasts: [],
    addToast: (toast) => {
      const id = Math.random().toString(36).slice(2, 9);
      set((state) => ({
        toasts: [...state.toasts, { ...toast, id }],
      });
      return id;
    },
    removeToast: (id) => set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
  };
});
