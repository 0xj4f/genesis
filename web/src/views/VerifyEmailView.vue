<template>
  <AuthLayout>
    <div v-if="loading" class="status">
      <span class="spinner status-spinner" aria-hidden="true"></span>
      <h1>Verifying your email…</h1>
    </div>

    <div v-else-if="verifiedEmail" class="status">
      <span class="status-icon ok" aria-hidden="true"><MailCheck :size="24" /></span>
      <h1>Email verified</h1>
      <p><strong>{{ verifiedEmail }}</strong> is confirmed. You're all set.</p>
      <router-link :to="isAuthenticated ? '/profile' : '/login'" class="btn btn-primary btn-block btn-lg mt-lg">
        {{ isAuthenticated ? 'Continue' : 'Sign in' }}
      </router-link>
    </div>

    <div v-else class="status">
      <span class="status-icon bad" aria-hidden="true"><MailX :size="24" /></span>
      <h1>This link didn't work</h1>
      <p>{{ error }}</p>
      <form class="stack-sm resend" @submit.prevent="resend">
        <label for="email" class="form-label">Send a new link to</label>
        <input v-model="email" id="email" type="email" inputmode="email" class="form-input"
               placeholder="you@company.com" autocomplete="email" autocapitalize="none" required />
        <button type="submit" class="btn btn-primary btn-block" :disabled="sending">Resend link</button>
      </form>
      <div v-if="notice" class="alert alert-success mt-md" role="status">
        <CircleCheck :size="18" aria-hidden="true" /><span>{{ notice }}</span>
      </div>
    </div>
  </AuthLayout>
</template>

<script>
import { mapGetters } from 'vuex';
import { MailCheck, MailX, CircleCheck } from 'lucide-vue-next';
import api from '@/api';
import AuthLayout from '@/components/ui/AuthLayout.vue';

export default {
  name: 'VerifyEmailView',
  components: { MailCheck, MailX, CircleCheck, AuthLayout },
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

<style scoped>
.resend { margin-top: var(--space-lg); text-align: left; }
</style>
