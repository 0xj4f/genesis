<template>
  <dialog ref="dialog" class="confirm" aria-labelledby="confirm-title" @cancel.prevent="settle(false)"
          @click="onBackdrop">
    <form method="dialog" class="confirm-body" @submit.prevent="settle(true)">
      <div class="confirm-icon" :class="{ danger: state.danger }" aria-hidden="true">
        <TriangleAlert v-if="state.danger" :size="20" />
        <CircleHelp v-else :size="20" />
      </div>
      <h2 id="confirm-title">{{ state.title }}</h2>
      <p v-if="state.message" class="confirm-msg">{{ state.message }}</p>

      <div v-if="state.requireText" class="form-group mt-md">
        <label for="confirm-text">Type <strong class="mono">{{ state.requireText }}</strong> to confirm</label>
        <input id="confirm-text" v-model="typed" class="form-input" autocomplete="off" autocapitalize="none"
               autocorrect="off" spellcheck="false" />
      </div>

      <div class="confirm-actions">
        <button type="button" class="btn btn-secondary" @click="settle(false)">Cancel</button>
        <button type="submit" class="btn" :class="state.danger ? 'btn-danger' : 'btn-primary'" :disabled="!canConfirm">
          {{ state.confirmLabel }}
        </button>
      </div>
    </form>
  </dialog>
</template>

<script>
import { TriangleAlert, CircleHelp } from 'lucide-vue-next';
import { confirmState, settleConfirm } from '@/utils/feedback';

export default {
  name: 'ConfirmDialog',
  components: { TriangleAlert, CircleHelp },
  data() {
    return { state: confirmState, typed: '' };
  },
  computed: {
    canConfirm() {
      return !this.state.requireText || this.typed.trim() === this.state.requireText;
    },
  },
  watch: {
    'state.open'(open) {
      const dialog = this.$refs.dialog;
      if (open) {
        this.typed = '';
        if (!dialog.open) dialog.showModal();
      } else if (dialog.open) {
        dialog.close();
      }
    },
  },
  methods: {
    settle(result) {
      if (result && !this.canConfirm) return;
      settleConfirm(result);
    },
    onBackdrop(event) {
      if (event.target === this.$refs.dialog) this.settle(false);
    },
  },
};
</script>

<style scoped>
.confirm {
  margin: auto auto 0;
  width: 100%;
  max-width: 100%;
  border: none;
  background: var(--surface);
  color: var(--text);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  box-shadow: var(--shadow-lg);
  padding: 0;
}

.confirm[open] { animation: sheet-up 240ms var(--ease-out); }
.confirm::backdrop { background: var(--overlay); }

@media (min-width: 640px) {
  .confirm { margin: auto; max-width: 420px; border-radius: var(--radius-xl); border: 1px solid var(--border); }
  .confirm[open] { animation: pop-in 180ms var(--ease-out); }
}

.confirm-body {
  padding: var(--space-lg) var(--space-lg) calc(var(--space-lg) + var(--safe-bottom));
}

@media (min-width: 640px) {
  .confirm-body { padding: var(--space-lg); }
}

.confirm-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-soft);
  color: var(--primary-text);
  margin-bottom: var(--space-md);
}

.confirm-icon.danger { background: var(--danger-soft); color: var(--danger); }

.confirm h2 { font-size: var(--text-lg); }
.confirm-msg { color: var(--text-muted); margin-top: var(--space-xs); font-size: var(--text-md); }

.confirm-actions {
  display: flex;
  flex-direction: column-reverse;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
}

.confirm-actions .btn { width: 100%; }

@media (min-width: 640px) {
  .confirm-actions { flex-direction: row; justify-content: flex-end; }
  .confirm-actions .btn { width: auto; }
}

@keyframes sheet-up { from { transform: translateY(100%); } to { transform: none; } }
@keyframes pop-in { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: none; } }
</style>
