<template>
  <AuthLayout>
    <div v-if="loading" class="status" role="status">
      <span class="spinner status-spinner" aria-hidden="true"></span>
      <h1>Completing sign in…</h1>
      <p>Hang tight while we confirm your account.</p>
    </div>
    <div v-else-if="error" class="status">
      <span class="status-icon bad" aria-hidden="true"><CircleAlert :size="24" /></span>
      <h1>Sign in didn't finish</h1>
      <p>{{ error }}</p>
      <router-link to="/login" class="btn btn-primary btn-block btn-lg mt-lg">Back to sign in</router-link>
    </div>
  </AuthLayout>
</template>

<script>
import { CircleAlert } from 'lucide-vue-next';
import api from '@/api';
import AuthLayout from '@/components/ui/AuthLayout.vue';
import { SSO_ERRORS } from '@/utils/messages';

export default {
  name: 'SSOCallbackView',
  components: { CircleAlert, AuthLayout },
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

