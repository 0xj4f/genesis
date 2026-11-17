<template>
  <AppSheet :open="open" title="New user" @close="$emit('close')">
    <form id="new-user-form" class="stack" novalidate @submit.prevent="submit">
      <div class="form-group">
        <label for="nu-username">Username</label>
        <input id="nu-username" v-model.trim="form.username" class="form-input" maxlength="100" required
               autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"
               :aria-invalid="errors.username ? 'true' : undefined" aria-describedby="nu-username-msg" />
        <p v-if="errors.username" id="nu-username-msg" class="form-error">{{ errors.username }}</p>
      </div>
      <div class="form-group">
        <label for="nu-email">Email</label>
        <input id="nu-email" v-model.trim="form.email" type="email" inputmode="email" class="form-input" required
               autocomplete="off" autocapitalize="none" :aria-invalid="errors.email ? 'true' : undefined"
               aria-describedby="nu-email-msg" />
        <p v-if="errors.email" id="nu-email-msg" class="form-error">{{ errors.email }}</p>
      </div>

      <div v-if="isRootAdmin" class="form-group">
        <span id="nu-role-label" class="form-label">Role</span>
        <div class="segmented role-picker" role="radiogroup" aria-labelledby="nu-role-label">
          <button v-for="role in ['user', 'admin']" :key="role" type="button" role="radio"
                  :aria-checked="String(form.role === role)" @click="form.role = role">{{ role }}</button>
        </div>
        <p class="form-hint">Admins manage regular users. Only root manages admins.</p>
      </div>

      <fieldset class="form-group">
        <legend class="form-label">Password</legend>
        <div class="radio-cards mt-xs">
          <label class="radio-card">
            <input v-model="form.mode" type="radio" value="generate" />
            <div><strong>Generate one-time password</strong><span>Shown once for you to send. They choose their own at first sign-in.</span></div>
          </label>
          <label class="radio-card">
            <input v-model="form.mode" type="radio" value="set" />
            <div><strong>Set a password</strong><span>Type one now, for example one you agreed with them.</span></div>
          </label>
        </div>
      </fieldset>

      <div v-if="form.mode === 'set'" class="form-group">
        <label for="nu-password">Password</label>
        <PasswordInput id="nu-password" v-model="form.password" autocomplete="new-password"
                       :invalid="!!errors.password" describedby="nu-password-msg" />
        <p id="nu-password-msg" :class="errors.password ? 'form-error' : 'form-hint'">
          {{ errors.password || '12+ characters with upper and lower case, a number and a symbol.' }}
        </p>
      </div>

      <div class="stack-sm">
        <label class="check" :class="{ locked: form.mode === 'generate' }">
          <input v-model="requireChange" type="checkbox" :disabled="form.mode === 'generate'" />
          <span>Require a new password at first sign-in</span>
        </label>
        <label class="check">
          <input v-model="form.emailVerified" type="checkbox" aria-describedby="nu-verified-hint" />
          <span>I've confirmed this email address belongs to them</span>
        </label>
        <p id="nu-verified-hint" class="form-hint">
          Leave unticked unless you're sure: a verified address lets a Google or GitHub sign-in with the same email join
          this account. With email verification required, they can't sign in until it's verified.
        </p>
      </div>

      <div v-if="error" class="alert alert-error" role="alert">
        <CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span>
      </div>
    </form>

    <template #footer>
      <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancel</button>
      <button type="submit" form="new-user-form" class="btn btn-primary spacer" :disabled="saving">
        <span v-if="saving" class="spinner" aria-hidden="true"></span>Create user
      </button>
    </template>

  </AppSheet>
  <OneTimePasswordDialog :issued="issued" heading="User created" @close="finish" />
</template>

<script>
import { mapGetters } from 'vuex';
import { CircleAlert } from 'lucide-vue-next';
import api from '@/api';
import AppSheet from '@/components/ui/AppSheet.vue';
import PasswordInput from '@/components/ui/PasswordInput.vue';
import OneTimePasswordDialog from '@/components/admin/OneTimePasswordDialog.vue';
import { passwordError } from '@/utils/validation';
import { toast } from '@/utils/feedback';

function blankForm() {
  return { username: '', email: '', role: 'user', mode: 'generate', password: '', requireChange: true, emailVerified: false };
}

// Create an account from the console with a generated (one-time) or chosen password.
export default {
  name: 'NewUserSheet',
  components: { CircleAlert, AppSheet, PasswordInput, OneTimePasswordDialog },
  props: { open: Boolean },
  emits: ['close', 'created'],
  data() {
    return {
      form: blankForm(),
      errors: {},
      error: '',
      saving: false,
      created: null,
      issued: null,
    };
  },
  computed: {
    ...mapGetters(['isRootAdmin']),
    // Generated passwords are always one-time.
    requireChange: {
      get() { return this.form.mode === 'generate' || this.form.requireChange; },
      set(value) { this.form.requireChange = value; },
    },
  },
  watch: {
    open(value) {
      if (value) {
        this.form = blankForm();
        this.errors = {};
        this.error = '';
        this.$nextTick(() => document.getElementById('nu-username')?.focus());
      }
    },
  },
  methods: {
    validate() {
      const errors = {};
      if (!this.form.username) errors.username = 'Enter a username.';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.form.email)) errors.email = 'Enter a valid email address.';
      if (this.form.mode === 'set') {
        const problem = passwordError(this.form.password);
        if (problem) errors.password = problem;
      }
      this.errors = errors;
      return !Object.keys(errors).length;
    },
    async submit() {
      this.error = '';
      if (!this.validate()) {
        this.$nextTick(() => document.querySelector('#new-user-form [aria-invalid="true"]')?.focus());
        return;
      }
      const body = {
        username: this.form.username,
        email: this.form.email,
        role: this.isRootAdmin ? this.form.role : 'user',
        email_verified: this.form.emailVerified,
        require_password_change: this.requireChange,
      };
      if (this.form.mode === 'set') body.password = this.form.password;
      this.saving = true;
      try {
        const result = await api.createAdminUser(body);
        this.created = result.user;
        if (result.temporary_password) this.issued = result;
        else this.finish();
      } catch (e) {
        this.error = e.message;
      } finally {
        this.saving = false;
      }
    },
    finish() {
      this.issued = null;
      toast(`${this.created.username} was created`);
      this.$emit('created', this.created);
    },
  },
};
</script>

<style scoped>
fieldset { border: none; }
.role-picker { width: 100%; }
.role-picker button { flex: 1; }
.check.locked { opacity: 0.7; }
</style>
