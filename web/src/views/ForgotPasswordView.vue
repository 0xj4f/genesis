<template>
  <AuthLayout>
    <div class="auth-header">
      <BrandMark large />
      <h1>{{ sent ? 'Request sent' : 'Forgot your password?' }}</h1>
      <p v-if="sent">{{ message }}</p>
      <p v-else>Enter your username or email. An administrator will send you a temporary password.</p>
    </div>

    <div v-if="sent" class="stack">
      <div class="alert">
        <Info :size="18" aria-hidden="true" />
        <span>Email delivery isn't set up yet, so the administrator will reach you directly. The temporary password works once: you'll choose a new one when you sign in.</span>
      </div>
      <router-link to="/login" class="btn btn-primary btn-block btn-lg">Back to sign in</router-link>
    </div>

    <form v-else class="stack" @submit.prevent="submit">
      <div class="form-group">
        <label for="identifier">Username or email</label>
        <input id="identifier" v-model.trim="identifier" class="form-input" autocomplete="username"
               autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="255" required />
      </div>

      <div v-if="error" class="alert alert-error" role="alert">
        <CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span>
      </div>

      <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="sending || !identifier">
        <span v-if="sending" class="spinner" aria-hidden="true"></span>
        {{ sending ? 'Sending…' : 'Request a reset' }}
      </button>
    </form>

    <p class="auth-footer-link">
      Remembered it?
      <router-link to="/login" class="link">Sign in</router-link>
    </p>
  </AuthLayout>
</template>

<script>
import { CircleAlert, Info } from 'lucide-vue-next';
import api from '@/api';
import AuthLayout from '@/components/ui/AuthLayout.vue';
import BrandMark from '@/components/ui/BrandMark.vue';

export default {
  name: 'ForgotPasswordView',
  components: { CircleAlert, Info, AuthLayout, BrandMark },
  data() {
    return { identifier: '', sending: false, sent: false, message: '', error: '' };
  },
  methods: {
    async submit() {
      this.error = '';
      this.sending = true;
      try {
        this.message = (await api.requestPasswordReset(this.identifier)).message;
        this.sent = true;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.sending = false;
      }
    },
  },
};
</script>
