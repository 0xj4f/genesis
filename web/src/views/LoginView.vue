<template>
  <div class="page-center">
    <div class="auth-card card">
      <div class="auth-header">
        <div class="brand-mark">&gt;_</div>
        <h1>genesis<span class="accent">_login</span></h1>
        <p class="text-muted">authenticate to continue</p>
      </div>

      <!-- SSO Buttons -->
      <div v-if="ssoProviders.length" class="stack">
        <a v-for="provider in ssoProviders" :key="provider"
           :href="ssoUrl(provider)" class="btn-sso">
          <SSOIcon :provider="provider" />
          Continue with {{ capitalize(provider) }}
        </a>
        <div class="divider">or sign in with credentials</div>
      </div>

      <!-- Native Login Form -->
      <form @submit.prevent="handleLogin" class="stack">
        <div class="form-group">
          <label for="username">Username</label>
          <input v-model="username" id="username" type="text" class="form-input"
                 placeholder="enter username" autocomplete="username" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input v-model="password" id="password" type="password" class="form-input"
                 placeholder="enter password" autocomplete="current-password" required />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="needsVerification" class="alert">
          <form @submit.prevent="resend" class="stack">
            <label for="verify-email" class="text-sm">Send a new verification link to:</label>
            <input v-model="verifyEmail" id="verify-email" type="email" class="form-input"
                   placeholder="you@domain.com" autocomplete="email" required />
            <button type="submit" class="btn btn-secondary btn-sm" :disabled="resending">Resend link</button>
          </form>
        </div>
        <div v-if="notice" class="alert alert-success">{{ notice }}</div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Authenticate</span>
        </button>
      </form>

      <p class="text-center text-sm mt-lg text-muted">
        No account?
        <router-link to="/register" class="link">Register</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import api from '@/api';
import SSOIcon from '@/components/SSOIcon.vue';
import { safeNextPath } from '@/utils/validation';

export default {
  name: 'LoginView',
  components: { SSOIcon },
  data() {
    return {
      username: '', password: '', error: '', loading: false,
      needsVerification: false, verifyEmail: '', resending: false, notice: '',
    };
  },
  computed: {
    ...mapState(['ssoProviders']),
  },
  created() {
    this.fetchSSOProviders();
  },
  methods: {
    ...mapActions(['login', 'fetchSSOProviders']),
    async handleLogin() {
      this.error = '';
      this.notice = '';
      this.needsVerification = false;
      this.loading = true;
      try {
        await this.login({ username: this.username, password: this.password });
        this.$router.replace(safeNextPath(this.$route.query.next) || '/profile');
      } catch (e) {
        this.error = e.message;
        this.needsVerification = e.status === 403 && e.message === 'Email address not verified';
      } finally {
        this.loading = false;
      }
    },
    async resend() {
      this.resending = true;
      try {
        const data = await api.resendVerification(this.verifyEmail);
        this.notice = data.message;
        this.needsVerification = false;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.resending = false;
      }
    },
    ssoUrl(provider) {
      return api.ssoAuthorizeUrl(provider);
    },
    capitalize(s) {
      return s.charAt(0).toUpperCase() + s.slice(1);
    },
  },
};
</script>

<style scoped>
.auth-card {
  width: 100%;
  max-width: 420px;
}

.auth-header {
  text-align: center;
  margin-bottom: var(--space-xl);
}

.auth-header h1 {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin-top: var(--space-md);
}

.accent {
  color: var(--accent);
}

.brand-mark {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  background: var(--bg-elevated);
  border: 1px solid var(--border-accent);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-xl);
  font-family: var(--font-mono);
}
</style>
