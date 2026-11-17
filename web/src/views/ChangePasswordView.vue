<template>
  <AuthLayout>
    <div class="auth-header">
      <BrandMark large />
      <h1>Choose a new password</h1>
      <p>
        You signed in with a temporary password from an administrator. Set your own to continue{{ expiry ? ` (the temporary one expires ${expiry})` : '' }}.
      </p>
    </div>

    <form class="stack" novalidate @submit.prevent="submit">
      <div v-if="needCurrent" class="form-group">
        <label for="current-password">Temporary password</label>
        <PasswordInput id="current-password" v-model="current" autocomplete="current-password" required />
      </div>
      <div class="form-group">
        <label for="new-password">New password</label>
        <PasswordInput id="new-password" v-model="newPassword" autocomplete="new-password" required
                       :invalid="!!problem" describedby="new-password-hint" />
        <p id="new-password-hint" :class="problem ? 'form-error' : 'form-hint'">
          {{ problem || `12+ characters with upper and lower case, a number and one of ${symbols}` }}
        </p>
      </div>
      <div class="form-group">
        <label for="confirm-password">Confirm new password</label>
        <PasswordInput id="confirm-password" v-model="confirm" autocomplete="new-password" required />
      </div>

      <div v-if="error" class="alert alert-error" role="alert">
        <CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span>
      </div>

      <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="saving">
        <span v-if="saving" class="spinner" aria-hidden="true"></span>
        {{ saving ? 'Saving…' : 'Set password and continue' }}
      </button>
    </form>

    <p class="auth-footer-link">
      Not now?
      <button type="button" class="link link-button" @click="signOut">Sign out</button>
    </p>
  </AuthLayout>
</template>

<script>
import { CircleAlert } from 'lucide-vue-next';
import api from '@/api';
import AuthLayout from '@/components/ui/AuthLayout.vue';
import BrandMark from '@/components/ui/BrandMark.vue';
import PasswordInput from '@/components/ui/PasswordInput.vue';
import { PASSWORD_SYMBOLS, passwordError, safeNextPath } from '@/utils/validation';
import { takePassword } from '@/utils/pendingPassword';
import { dateTime } from '@/utils/format';
import { toast } from '@/utils/feedback';

// Forced password change for accounts holding a temporary password. Serves
// both the user app and the admin console (route meta.kind).
export default {
  name: 'ChangePasswordView',
  components: { CircleAlert, AuthLayout, BrandMark, PasswordInput },
  data() {
    const current = takePassword(this.$route.meta.kind);
    return {
      current,
      needCurrent: !current,
      newPassword: '',
      confirm: '',
      problem: '',
      error: '',
      saving: false,
      symbols: PASSWORD_SYMBOLS,
    };
  },
  computed: {
    kind() { return this.$route.meta.kind; },
    account() { return this.kind === 'admin' ? this.$store.state.adminUser : this.$store.state.user; },
    expiry() { return this.account?.password_expires_at ? dateTime(this.account.password_expires_at) : ''; },
  },
  methods: {
    async submit() {
      this.error = '';
      this.problem = passwordError(this.newPassword, this.confirm);
      if (this.problem) return;
      if (!this.current) {
        this.error = 'Enter the temporary password you signed in with.';
        return;
      }
      if (this.newPassword === this.current) {
        this.problem = 'Choose a password different from the temporary one.';
        return;
      }
      this.saving = true;
      try {
        await api.changePassword(this.current, this.newPassword, this.kind);
      } catch (e) {
        this.error = e.message;
        if (e.status === 400 && /current password/i.test(e.message)) this.needCurrent = true;
        this.saving = false;
        return;
      }
      // The change is done: forget the temporary password so nothing below can resubmit it.
      Object.assign(this, { current: '', needCurrent: true, newPassword: '', confirm: '' });
      toast('Password updated');
      try {
        await this.finish();
      } catch (e) {
        this.error = `Your password was changed, but loading your account failed (${e.message}). Sign in again with your new password.`;
      } finally {
        this.saving = false;
      }
    },
    async finish() {
      const admin = this.kind === 'admin';
      this.$store.commit(admin ? 'setAdminUser' : 'setUser', { ...this.account, must_change_password: false });
      // Tokens issued with the temporary password only allow this change; swap them.
      if (!(await this.$store.dispatch('refreshSession', this.kind))) return;
      const next = safeNextPath(this.$route.query.next);
      if (admin) {
        this.$store.commit('setAdminUser', await api.getAdminMe());
        this.$router.replace(next?.startsWith('/admin/') ? next : '/admin');
        return;
      }
      await Promise.all([this.$store.dispatch('fetchMe'), this.$store.dispatch('fetchProfile')]);
      const fallback = this.$store.getters.hasProfile ? '/profile' : '/profile/create';
      this.$router.replace(next && next !== '/profile' ? next : fallback);
    },
    signOut() {
      this.$store.dispatch(this.kind === 'admin' ? 'adminLogout' : 'logout');
    },
  },
};
</script>

<style scoped>
.link-button { background: none; border: none; padding: 0; font: inherit; cursor: pointer; }
</style>
