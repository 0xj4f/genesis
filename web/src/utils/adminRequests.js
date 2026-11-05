import { reactive } from 'vue';
import api from '@/api';

// Open account-request count for the admin nav badge, shared by the views that
// change it. Refreshed on a timer by AdminLayout and after request actions.
export const requestCounts = reactive({ open: 0 });

export async function refreshRequestCount() {
  try {
    requestCounts.open = (await api.getRequestSummary()).open;
  } catch {
    /* keep the last count; the next refresh retries */
  }
}

export const REQUEST_CATEGORIES = {
  password_reset: 'Password reset',
};
