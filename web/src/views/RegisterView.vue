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

      <div v-if="pendingEmail" class="stack">
        <div class="alert alert-success">
          Check {{ pendingEmail }} for a verification link, then sign in.
        </div>
        <button class="btn btn-secondary btn-block" :disabled="loading" @click="resend">Resend link</button>
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>
        <router-link to="/login" class="btn btn-primary btn-block">Go to sign in</router-link>
      </div>

      <form v-else @submit.prevent="handleRegister" class="stack">
        <div class="form-group">
          <label for="username">Username</label>
          <input v-model="username" id="username" type="text" class="form-input"
                 placeholder="choose a handle" autocomplete="username" maxlength="100" required />
        </div>
        <div class="form-group">
          <label for="email">Email</label>
          <input v-model="email" id="email" type="email" class="form-input"
                 placeholder="you@domain.com" autocomplete="email" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input v-model="password" id="password" type="password" class="form-input"
                 :placeholder="`12-128 chars, mixed case, number, one of ${symbols}`"
                 autocomplete="new-password" minlength="12" maxlength="128" required />
        </div>
        <div class="form-group">
          <label for="confirm">Confirm password</label>
          <input v-model="confirm" id="confirm" type="password" class="form-input"
                 placeholder="repeat password" autocomplete="new-password" required />
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
import { PASSWORD_SYMBOLS, passwordError } from '@/utils/validation';

export default {
  name: 'RegisterView',
  components: { SSOIcon },
  data() {
    return {
      username: '', email: '', password: '', confirm: '',
      error: '', success: '', loading: false, pendingEmail: '', symbols: PASSWORD_SYMBOLS,
    };
  },
  computed: {
    ...mapState(['ssoProviders', 'authConfig']),
  },
  created() {
    this.fetchSSOProviders();
    this.fetchAuthConfig();
  },
  methods: {
    ...mapActions(['login', 'fetchSSOProviders', 'fetchAuthConfig']),
    async handleRegister() {
      this.error = passwordError(this.password, this.confirm);
      this.success = '';
      if (this.error) return;
      this.loading = true;
      try {
        await api.register(this.username, this.email, this.password);
        if (this.authConfig.email_verification) {
          // Sign-in waits until the address is verified.
          this.pendingEmail = this.email;
          this.password = '';
          this.confirm = '';
          return;
        }
        await this.login({ username: this.username, password: this.password });
        this.$router.push('/profile/create');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    async resend() {
      this.error = '';
      this.loading = true;
      try {
        this.success = (await api.resendVerification(this.pendingEmail)).message;
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
