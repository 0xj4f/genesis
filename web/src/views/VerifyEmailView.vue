<template>
  <div class="page-center">
    <div class="card text-center" style="max-width: 420px; width: 100%;">
      <div v-if="loading" class="stack" style="align-items: center;">
        <div class="spinner" style="width: 32px; height: 32px;"></div>
        <p class="text-muted">Verifying your email...</p>
      </div>
      <div v-else-if="verifiedEmail" class="stack">
        <h2>Email verified</h2>
        <div class="alert alert-success">{{ verifiedEmail }} is confirmed.</div>
        <router-link :to="isAuthenticated ? '/profile' : '/login'" class="btn btn-primary btn-block">Continue</router-link>
      </div>
      <div v-else class="stack">
        <h2>Verification failed</h2>
        <div class="alert alert-error">{{ error }}</div>
        <form @submit.prevent="resend" class="stack">
          <label for="email" class="text-sm text-muted">Send a new link to:</label>
          <input v-model="email" id="email" type="email" class="form-input" autocomplete="email" required />
          <button type="submit" class="btn btn-secondary btn-block" :disabled="sending">Resend link</button>
        </form>
        <div v-if="notice" class="alert alert-success">{{ notice }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import api from '@/api';

export default {
  name: 'VerifyEmailView',
  data() {
    return { loading: true, verifiedEmail: '', error: '', email: '', sending: false, notice: '' };
  },
  computed: {
    ...mapGetters(['isAuthenticated']),
  },
  async created() {
    // Token is in the fragment (not sent to servers); clear it from history.
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
    window.history.replaceState(window.history.state, '', window.location.pathname);
    if (!token) {
      this.error = 'This verification link is incomplete.';
      this.loading = false;
      return;
    }
    try {
      const data = await api.verifyEmail(token);
      this.verifiedEmail = data.email;
      if (this.isAuthenticated) await this.$store.dispatch('fetchMe');
    } catch (e) {
      this.error = e.message;
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async resend() {
      this.sending = true;
      try {
        this.notice = (await api.resendVerification(this.email)).message;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.sending = false;
      }
    },
  },
};
</script>
