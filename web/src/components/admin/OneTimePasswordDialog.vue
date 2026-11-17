<template>
  <dialog ref="dialog" class="modal" aria-labelledby="otp-title" @cancel.prevent @close="onClose">
    <div v-if="issued" class="modal-body">
      <div class="modal-icon" aria-hidden="true"><KeyRound :size="20" /></div>
      <h2 id="otp-title">{{ heading }}</h2>
      <p class="text-muted text-md mt-xs">
        Send this to <strong>{{ issued.username }}</strong> yourself, through a channel you trust. They'll choose a new
        password the first time they sign in.
      </p>

      <div class="form-group mt-md">
        <span class="form-label">Temporary password</span>
        <div class="secret-box">
          <code class="mono password">{{ issued.temporary_password }}</code>
          <CopyButton :value="issued.temporary_password" what="temporary password" />
        </div>
        <p v-if="expiry" class="form-hint">Works until {{ expiry }}. It is shown only once.</p>
      </div>

      <div class="form-group mt-md">
        <span class="form-label">Message to send</span>
        <pre class="message">{{ message }}</pre>
        <div>
          <CopyButton :value="message" what="message" label="Copy message" size="md" />
        </div>
      </div>

      <label class="check mt-lg">
        <input v-model="sent" type="checkbox" />
        <span>I've sent this to {{ issued.username }}</span>
      </label>

      <button class="btn btn-primary btn-block mt-md" :disabled="!sent" @click="$refs.dialog.close()">Done</button>
    </div>
  </dialog>
</template>

<script>
import { KeyRound } from 'lucide-vue-next';
import CopyButton from '@/components/ui/CopyButton.vue';
import { dateTime } from '@/utils/format';

// One-time display of an admin-issued temporary password (the API's
// IssuedPassword), with a ready-to-send message since there is no email yet.
// Open while `issued` is set; emits close when dismissed, including when the
// browser closes it (repeated Esc in Chromium).
export default {
  name: 'OneTimePasswordDialog',
  components: { KeyRound, CopyButton },
  props: {
    issued: { type: Object, default: null },
    heading: { type: String, default: 'Temporary password ready' },
  },
  emits: ['close'],
  data() {
    return { sent: false };
  },
  computed: {
    expiry() { return this.issued?.password_expires_at ? dateTime(this.issued.password_expires_at) : ''; },
    // Admin accounts sign in to the console instead of the user app.
    signInUrl() {
      return `${window.location.origin}${this.issued?.role === 'user' ? '/login' : '/admin/login'}`;
    },
    message() {
      const { username, temporary_password: password } = this.issued;
      const lines = [
        `Hi ${username},`,
        '',
        'Here is your temporary Genesis password:',
        password,
        '',
        `Sign in at ${this.signInUrl} with your username (${username}).`,
        "You'll be asked to choose a new password straight away.",
      ];
      if (this.expiry) lines.push(`This temporary password stops working on ${this.expiry}.`);
      return lines.join('\n');
    },
  },
  watch: {
    issued: {
      handler(value) {
        this.$nextTick(() => {
          const dialog = this.$refs.dialog;
          if (value && !dialog.open) {
            this.sent = false;
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
    onClose() {
      if (this.issued) this.$emit('close');
    },
  },
};
</script>

<style scoped>
.password { font-size: var(--text-base); letter-spacing: 0.02em; }

.message {
  margin: 0;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--text-muted);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
