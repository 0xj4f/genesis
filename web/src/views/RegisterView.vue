<template>
  <div class="page-center">
    <div class="auth-card card">
      <div class="auth-header">
        <div class="brand-mark">&gt;_</div>
        <h1>genesis<span class="accent">_register</span></h1>
        <p class="text-muted">create a new identity</p>
      </div>

      <!-- SSO Buttons -->
      <div v-if="ssoProviders.length" class="stack">
        <a v-for="provider in ssoProviders" :key="provider"
           :href="ssoUrl(provider)" class="btn-sso">
          <SSOIcon :provider="provider" />
          Sign up with {{ capitalize(provider) }}
        </a>
        <div class="divider">or register with credentials</div>
      </div>

      <form @submit.prevent="handleRegister" class="stack">
        <div class="form-group">
          <label for="username">Username</label>
          <input v-model="username" id="username" type="text" class="form-input"
                 placeholder="choose a handle" required />
        </div>
        <div class="form-group">
          <label for="email">Email</label>
          <input v-model="email" id="email" type="email" class="form-input"
                 placeholder="you@domain.com" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input v-model="password" id="password" type="password" class="form-input"
                 placeholder="min 12 chars, mixed case, number, symbol" required />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Create Identity</span>
        </button>
      </form>

      <p class="text-center text-sm mt-lg text-muted">
        Already registered?
        <router-link to="/login" class="link">Authenticate</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import api from '@/api';
import SSOIcon from '@/components/SSOIcon.vue';

export default {
  name: 'RegisterView',
  components: { SSOIcon },
  data() {
    return { username: '', email: '', password: '', error: '', success: '', loading: false };
  },
  computed: {
    ...mapState(['ssoProviders']),
  },
  created() {
    this.fetchSSOProviders();
  },
  methods: {
    ...mapActions(['login', 'fetchSSOProviders']),
    async handleRegister() {
      this.error = '';
      this.success = '';
      this.loading = true;
      try {
        await api.register(this.username, this.email, this.password);
        await this.login({ username: this.username, password: this.password });
        this.$router.push('/profile/create');
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
