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
                 placeholder="enter username" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input v-model="password" id="password" type="password" class="form-input"
                 placeholder="enter password" required />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

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

export default {
  name: 'LoginView',
  components: { SSOIcon },
  data() {
    return { username: '', password: '', error: '', loading: false };
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
      this.loading = true;
      try {
        await this.login({ username: this.username, password: this.password });
        this.$router.push('/profile');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
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
