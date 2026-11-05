<template>
  <dialog ref="dialog" class="reveal" aria-labelledby="reveal-title" @cancel.prevent>
    <div class="reveal-body">
      <div class="reveal-icon" aria-hidden="true"><KeyRound :size="20" /></div>
      <h2 id="reveal-title">{{ heading }}</h2>
      <p class="text-muted text-md mt-xs">
        Copy the client secret for <strong>{{ clientName }}</strong> and store it somewhere safe, such as a secrets manager.
      </p>

      <div class="alert alert-warning mt-md">
        <TriangleAlert :size="18" aria-hidden="true" />
        <span>This secret is shown only once. If you lose it, rotate it to get a new one.</span>
      </div>

      <div class="form-group mt-md">
        <span class="form-label">Client ID</span>
        <div class="secret-box">
          <code class="mono wrap-anywhere">{{ clientId }}</code>
          <CopyButton :value="clientId" what="client ID" />
        </div>
      </div>
      <div class="form-group mt-md">
        <span class="form-label">Client secret</span>
        <div class="secret-box">
          <code class="mono wrap-anywhere">{{ secret }}</code>
          <CopyButton :value="secret" what="client secret" />
        </div>
      </div>

      <label class="check mt-lg">
        <input v-model="stored" type="checkbox" />
        <span>I've stored this secret securely</span>
      </label>

      <button class="btn btn-primary btn-block mt-md" :disabled="!stored" @click="done">Done</button>
    </div>
  </dialog>
</template>

<script>
import { KeyRound, TriangleAlert } from 'lucide-vue-next';
import CopyButton from '@/components/ui/CopyButton.vue';

// One-time secret display after creating a client or rotating its secret.
// It stays open (Esc and backdrop are ignored) until the admin confirms.
export default {
  name: 'SecretRevealDialog',
  components: { KeyRound, TriangleAlert, CopyButton },
  props: {
    secret: { type: String, default: '' },
    clientId: { type: String, default: '' },
    clientName: { type: String, default: '' },
    heading: { type: String, default: 'Save your client secret' },
  },
  emits: ['close'],
  data() {
    return { stored: false };
  },
  watch: {
    secret: {
      handler(value) {
        this.$nextTick(() => {
          const dialog = this.$refs.dialog;
          if (value && !dialog.open) {
            this.stored = false;
            dialog.showModal();
          } else if (!value && dialog.open) {
            dialog.close();
          }
        });
      },
      immediate: true,
    },
  },
  methods: {
    done() {
      this.$refs.dialog.close();
      this.$emit('close');
    },
  },
};
</script>

<style scoped>
.reveal {
  margin: auto;
  width: calc(100% - 2 * var(--space-md));
  max-width: 480px;
  max-height: calc(100dvh - var(--safe-top) - var(--safe-bottom) - 2 * var(--space-md));
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-lg);
  padding: 0;
}

.reveal[open] { animation: pop-in 200ms var(--ease-out); }
.reveal::backdrop { background: var(--overlay); }
.reveal-body { padding: var(--space-lg); }

.reveal-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--warning-soft);
  color: var(--warning);
  margin-bottom: var(--space-md);
}

.reveal h2 { font-size: var(--text-lg); }

.secret-box {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 8px 6px 8px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.secret-box code { flex: 1; font-size: var(--text-sm); user-select: all; }

@keyframes pop-in { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: none; } }
</style>
