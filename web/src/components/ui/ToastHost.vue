<template>
  <div class="toast-host" aria-live="polite" role="status">
    <transition-group name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="`toast-${t.type}`">
        <CircleCheck v-if="t.type === 'success'" :size="18" aria-hidden="true" />
        <CircleAlert v-else :size="18" aria-hidden="true" />
        <span class="toast-msg">{{ t.message }}</span>
        <button class="toast-close" aria-label="Dismiss notification" @click="dismissToast(t.id)">
          <X :size="16" aria-hidden="true" />
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script>
import { CircleCheck, CircleAlert, X } from 'lucide-vue-next';
import { toasts, dismissToast } from '@/utils/feedback';

export default {
  name: 'ToastHost',
  components: { CircleCheck, CircleAlert, X },
  setup() {
    return { toasts, dismissToast };
  },
};
</script>

<style scoped>
.toast-host {
  position: fixed;
  z-index: var(--z-toast);
  left: 50%;
  transform: translateX(-50%);
  top: calc(var(--safe-top) + var(--space-sm));
  width: min(420px, calc(100vw - 2 * var(--space-md)));
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  pointer-events: none;
}

@media (min-width: 768px) {
  .toast-host { top: auto; left: auto; transform: none; right: var(--space-lg); bottom: var(--space-lg); }
}

.toast {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  font-size: var(--text-md);
}

.toast-success > svg { color: var(--success); flex-shrink: 0; }
.toast-error > svg { color: var(--danger); flex-shrink: 0; }
.toast-msg { flex: 1; min-width: 0; overflow-wrap: anywhere; }

.toast-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: var(--text-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  flex-shrink: 0;
}

.toast-close:hover { background: var(--surface-hover); color: var(--text); }

.toast-enter-active { transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out); }
.toast-leave-active { transition: opacity 140ms ease-in; }
.toast-enter-from { opacity: 0; transform: translateY(-8px); }
.toast-leave-to { opacity: 0; }

@media (min-width: 768px) {
  .toast-enter-from { transform: translateY(8px); }
}
</style>
