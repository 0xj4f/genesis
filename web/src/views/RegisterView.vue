<template>
  <div class="page-center">
    <div class="auth-card card">
      <div class="auth-header">
        <div class="brand-icon-lg">G</div>
        <h1>Create account</h1>
        <p class="text-muted">Get started with Genesis</p>
      </div>

      <!-- SSO Buttons -->
      <div v-if="ssoProviders.length" class="stack">
        <a v-for="provider in ssoProviders" :key="provider"
           :href="ssoUrl(provider)" class="btn-sso">
          <SSOIcon :provider="provider" />
          Sign up with {{ capitalize(provider) }}
        </a>
        <div class="divider">or</div>
      </div>

      <form @submit.prevent="handleRegister" class="stack">
        <div class="form-group">
          <label for="username">Username</label>
          <input v-model="username" id="username" type="text" class="form-input"
                 placeholder="Choose a username" required />
        </div>
        <div class="form-group">
          <label for="email">Email</label>
          <input v-model="email" id="email" type="email" class="form-input"
                 placeholder="you@example.com" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input v-model="password" id="password" type="password" class="form-input"
                 placeholder="Min 12 chars, upper, lower, number, special" required />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Create Account</span>
        </button>
      </form>

      <p class="text-center text-sm mt-lg text-muted">
        Already have an account?
        <router-link to="/login" class="link">Sign in</router-link>
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
        // Auto-login after registration
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
  max-width: 400px;
}

.auth-header {
  text-align: center;
  margin-bottom: var(--space-xl);
}

.auth-header h1 {
  font-size: var(--text-2xl);
  font-weight: 600;
  margin-top: var(--space-md);
}

.brand-icon-lg {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  background: var(--accent-gradient);
  color: var(--text-on-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-xl);
}
</style>
