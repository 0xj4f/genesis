import { reactive } from 'vue';

// App-wide toasts and confirmation dialog, rendered once by App.vue
// (ToastHost, ConfirmDialog) and driven from any view.

export const toasts = reactive([]);
let nextToastId = 1;

export function toast(message, type = 'success') {
  const id = nextToastId++;
  toasts.push({ id, message, type });
  setTimeout(() => dismissToast(id), type === 'error' ? 6000 : 4000);
}

export function dismissToast(id) {
  const index = toasts.findIndex(t => t.id === id);
  if (index !== -1) toasts.splice(index, 1);
}

export const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmLabel: 'Confirm',
  danger: false,
  // When set, the user must type this value before confirming.
  requireText: '',
  resolve: null,
});

// Resolves true when confirmed, false when cancelled.
export function confirmAction({ title, message = '', confirmLabel = 'Confirm', danger = false, requireText = '' }) {
  if (confirmState.resolve) confirmState.resolve(false);
  return new Promise(resolve => {
    Object.assign(confirmState, { open: true, title, message, confirmLabel, danger, requireText, resolve });
  });
}

export function settleConfirm(result) {
  const { resolve } = confirmState;
  Object.assign(confirmState, { open: false, resolve: null });
  if (resolve) resolve(result);
}
