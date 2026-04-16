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
import { mapActions } from 'vuex';

export default {
  name: 'SSOCallbackView',
  data() {
    return { loading: true, error: '' };
  },
  async created() {
    // SSO callback returns tokens as query params or JSON
    // The backend callback endpoint returns JSON directly
    // In a real flow, the backend would redirect to this page with tokens in the URL hash or query
    const params = new URLSearchParams(window.location.search);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (accessToken) {
      try {
        this.handleSSOTokens({ access_token: accessToken, refresh_token: refreshToken });
        await this.fetchProfile();
        const hasProfile = this.$store.getters.hasProfile;
        this.$router.push(hasProfile ? '/profile' : '/profile/create');
      } catch (e) {
        this.error = e.message;
      }
    } else {
      this.error = 'No authentication tokens received.';
    }
    this.loading = false;
  },
  methods: {
    ...mapActions(['handleSSOTokens', 'fetchProfile']),
  },
};
</script>
