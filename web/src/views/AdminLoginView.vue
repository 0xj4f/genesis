<template>
  <AuthLayout>
    <div class="auth-header">
      <BrandMark large />
      <span class="badge badge-warning admin-chip"><ShieldCheck :size="13" aria-hidden="true" />Admin console</span>
      <h1>Sign in to the admin console</h1>
      <p>For administrators of this Genesis tenant.</p>
    </div>

    <form class="stack" @submit.prevent="handleLogin">
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

      <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
        <span v-if="loading" class="spinner" aria-hidden="true"></span>
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>

    <p class="auth-footer-link">
      Not an administrator?
      <router-link to="/login" class="link">Go to user sign in</router-link>
    </p>
  </AuthLayout>
</template>

<script>
import { mapActions } from 'vuex';
import { CircleAlert, ShieldCheck } from 'lucide-vue-next';
import AuthLayout from '@/components/ui/AuthLayout.vue';
import BrandMark from '@/components/ui/BrandMark.vue';
import PasswordInput from '@/components/ui/PasswordInput.vue';
import { safeNextPath } from '@/utils/validation';

export default {
  name: 'AdminLoginView',
  components: { CircleAlert, ShieldCheck, AuthLayout, BrandMark, PasswordInput },
  data() {
    return { username: '', password: '', error: '', loading: false };
  },
  methods: {
    ...mapActions(['adminLogin']),
    async handleLogin() {
      this.error = '';
      this.loading = true;
      try {
        await this.adminLogin({ username: this.username, password: this.password });
        const next = safeNextPath(this.$route.query.next);
        this.$router.replace(next?.startsWith('/admin/') ? next : '/admin');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.auth-header { display: flex; flex-direction: column; align-items: flex-start; }
.auth-header .brand-mark { margin-bottom: var(--space-md); }
.admin-chip { margin-bottom: var(--space-sm); }
</style>
