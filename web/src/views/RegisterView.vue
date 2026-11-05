<template>
  <AuthLayout>
    <div class="auth-header">
      <BrandMark large />
      <h1>{{ pendingEmail ? 'Check your email' : 'Create your account' }}</h1>
      <p v-if="pendingEmail">We sent a verification link to <strong>{{ pendingEmail }}</strong>. Open it, then sign in.</p>
      <p v-else>One identity for every app connected to Genesis.</p>
    </div>

    <div v-if="pendingEmail" class="stack">
      <div v-if="error" class="alert alert-error" role="alert"><CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span></div>
      <div v-if="success" class="alert alert-success" role="status"><CircleCheck :size="18" aria-hidden="true" /><span>{{ success }}</span></div>
      <router-link to="/login" class="btn btn-primary btn-block btn-lg">Go to sign in</router-link>
      <button class="btn btn-ghost btn-block" :disabled="loading" @click="resend">Didn't get it? Resend link</button>
    </div>

    <template v-else>
      <!-- SSO Buttons -->
      <div v-if="ssoProviders.length" class="stack-sm">
        <a v-for="provider in ssoProviders" :key="provider" :href="ssoUrl(provider)" class="btn-sso">
          <SSOIcon :provider="provider" aria-hidden="true" />
          Sign up with {{ providerName(provider) }}
        </a>
        <div class="divider mt-sm">or</div>
      </div>

      <form class="stack" :class="{ 'mt-sm': ssoProviders.length }" novalidate @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username">Username</label>
          <input v-model="username" id="username" type="text" class="form-input" autocomplete="username"
                 autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="100" required />
        </div>
        <div class="form-group">
          <label for="email">Email</label>
          <input v-model="email" id="email" type="email" inputmode="email" class="form-input"
                 placeholder="you@company.com" autocomplete="email" autocapitalize="none" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <PasswordInput id="password" v-model="password" autocomplete="new-password" required
                         :invalid="!!passwordProblem" describedby="password-hint" @blur="checkPassword" />
          <p id="password-hint" :class="passwordProblem ? 'form-error' : 'form-hint'">
            {{ passwordProblem || `12+ characters with upper and lower case, a number and one of ${symbols}` }}
          </p>
        </div>
        <div class="form-group">
          <label for="confirm">Confirm password</label>
          <PasswordInput id="confirm" v-model="confirm" autocomplete="new-password" required
                         :invalid="!!confirmProblem" describedby="confirm-msg" />
          <p v-if="confirmProblem" id="confirm-msg" class="form-error">{{ confirmProblem }}</p>
        </div>

        <div v-if="error" class="alert alert-error" role="alert"><CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span></div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
          {{ loading ? 'Creating account…' : 'Create account' }}
        </button>
      </form>
    </template>

    <p class="auth-footer-link">
      Already have an account?
      <router-link to="/login" class="link">Sign in</router-link>
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
import { PASSWORD_SYMBOLS, passwordError } from '@/utils/validation';
import { providerName } from '@/utils/messages';

export default {
  name: 'RegisterView',
  components: { CircleAlert, CircleCheck, SSOIcon, AuthLayout, BrandMark, PasswordInput },
  data() {
    return {
      username: '', email: '', password: '', confirm: '',
      error: '', success: '', loading: false, pendingEmail: '', symbols: PASSWORD_SYMBOLS,
      passwordProblem: '', confirmProblem: '',
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
    providerName,
    checkPassword() {
      this.passwordProblem = this.password ? passwordError(this.password) : '';
    },
    async handleRegister() {
      this.error = '';
      this.success = '';
      this.passwordProblem = passwordError(this.password);
      this.confirmProblem = !this.passwordProblem && this.confirm !== this.password ? 'Passwords do not match.' : '';
      if (!this.username || !this.email) this.error = 'Enter a username and email.';
      if (this.error || this.passwordProblem || this.confirmProblem) return;
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
  },
};
</script>
