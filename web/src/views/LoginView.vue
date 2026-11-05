<template>
  <AuthLayout>
    <div class="auth-header">
      <BrandMark large />
      <h1>Sign in to Genesis</h1>
      <p>Welcome back. Use your account or a connected provider.</p>
    </div>

    <!-- SSO Buttons -->
    <div v-if="ssoProviders.length" class="stack-sm">
      <a v-for="provider in ssoProviders" :key="provider" :href="ssoUrl(provider)" class="btn-sso">
        <SSOIcon :provider="provider" aria-hidden="true" />
        Continue with {{ providerName(provider) }}
      </a>
      <div class="divider mt-sm">or</div>
    </div>

    <!-- Native Login Form -->
    <form class="stack" :class="{ 'mt-sm': ssoProviders.length }" @submit.prevent="handleLogin">
      <div class="form-group">
        <label for="username">Username</label>
        <input v-model="username" id="username" type="text" class="form-input" autocomplete="username"
               autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="next" required />
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <PasswordInput id="password" v-model="password" autocomplete="current-password" required
                       :invalid="!!error" :describedby="error ? 'login-error' : ''" />
      </div>

      <div v-if="error" id="login-error" class="alert alert-error" role="alert">
        <CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span>
      </div>
      <div v-if="notice" class="alert alert-success" role="status">
        <CircleCheck :size="18" aria-hidden="true" /><span>{{ notice }}</span>
      </div>

      <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
        <span v-if="loading" class="spinner" aria-hidden="true"></span>
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>

    <div v-if="needsVerification" class="alert alert-warning mt-md">
      <form class="stack-sm spacer" @submit.prevent="resend">
        <label for="verify-email" class="form-label">Your email isn't verified yet. Send a new link to</label>
        <input v-model="verifyEmail" id="verify-email" type="email" class="form-input" inputmode="email"
               placeholder="you@company.com" autocomplete="email" autocapitalize="none" required />
        <button type="submit" class="btn btn-secondary btn-sm" :disabled="resending">Resend link</button>
      </form>
    </div>

    <p class="auth-footer-link">
      New to Genesis?
      <router-link to="/register" class="link">Create an account</router-link>
    </p>
  </AuthLayout>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { CircleAlert, CircleCheck } from 'lucide-vue-next';
import api from '@/api';
import SSOIcon from '@/components/SSOIcon.vue';
import AuthLayout from '@/components/ui/AuthLayout.vue';
import BrandMark from '@/components/ui/BrandMark.vue';
import PasswordInput from '@/components/ui/PasswordInput.vue';
import { safeNextPath } from '@/utils/validation';
import { providerName } from '@/utils/messages';

export default {
  name: 'LoginView',
  components: { CircleAlert, CircleCheck, SSOIcon, AuthLayout, BrandMark, PasswordInput },
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
    providerName,
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
        this.error = '';
      } catch (e) {
        this.error = e.message;
      } finally {
        this.resending = false;
      }
    },
    ssoUrl(provider) {
      return api.ssoAuthorizeUrl(provider);
    },
  },
};
</script>
