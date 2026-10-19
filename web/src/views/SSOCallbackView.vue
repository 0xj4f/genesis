<template>
  <div class="page-center">
    <div class="card text-center" style="max-width: 400px; width: 100%;">
      <div v-if="loading" class="stack" style="align-items: center;">
        <div class="spinner" style="width: 32px; height: 32px;"></div>
        <p class="text-muted">Completing sign in...</p>
      </div>
      <div v-else-if="error" class="stack">
        <h2>Sign in failed</h2>
        <div class="alert alert-error">{{ error }}</div>
        <router-link to="/login" class="btn btn-primary btn-block">Back to Login</router-link>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/api';
import { SSO_ERRORS } from '@/utils/messages';

export default {
  name: 'SSOCallbackView',
  data() {
    return { loading: true, error: '' };
  },
  async created() {
    // The API redirects here with a one-time code (or an error code) in the URL
    // fragment, which browsers never send to servers. Remove it from the
    // address bar and history straight away.
    const params = new URLSearchParams(window.location.hash.slice(1));
    window.history.replaceState(window.history.state, '', window.location.pathname);

    const errorCode = params.get('error');
    const code = params.get('code');
    if (errorCode || !code) {
      this.error = SSO_ERRORS[errorCode] || SSO_ERRORS.sso_failed;
      this.loading = false;
      return;
    }
    try {
      // Only redeemable in the browser that went through the provider.
      const tokens = await api.ssoExchange(code);
      await this.$store.dispatch('completeLogin', tokens);
      const linked = params.get('linked');
      if (linked) {
        this.$router.replace({ path: '/profile', query: { linked } });
      } else {
        this.$router.replace(this.$store.getters.hasProfile ? '/profile' : '/profile/create');
      }
    } catch (e) {
      this.error = e.status === 400 ? SSO_ERRORS.invalid_request : e.message;
      this.loading = false;
    }
  },
};
</script>
