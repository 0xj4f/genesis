<template>
  <div class="page-center">
    <div class="card" style="max-width: 440px; width: 100%;">
      <div v-if="loading" class="stack" style="align-items: center;">
        <div class="spinner" style="width: 32px; height: 32px;"></div>
        <p class="text-muted">Checking the request...</p>
      </div>
      <div v-else-if="error" class="stack">
        <h2>Authorization failed</h2>
        <div class="alert alert-error">{{ error }}</div>
      </div>
      <div v-else class="stack">
        <h2>Allow {{ client.client_name }}?</h2>
        <p class="text-muted text-sm">
          Signed in as <strong>{{ currentUser?.username }}</strong>. {{ client.client_name }} is asking to:
        </p>
        <ul class="scope-list">
          <li v-for="scope in scopes" :key="scope">{{ describe(scope) }}</li>
        </ul>
        <div class="row">
          <button class="btn btn-primary" :disabled="deciding" @click="decide('approve')">Allow</button>
          <button class="btn btn-secondary" :disabled="deciding" @click="decide('deny')">Deny</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import api from '@/api';
import { SCOPE_DESCRIPTIONS } from '@/utils/messages';

const PARAMS = ['response_type', 'client_id', 'redirect_uri', 'scope', 'state', 'nonce', 'code_challenge', 'code_challenge_method'];

export default {
  name: 'ConsentView',
  data() {
    return { loading: true, deciding: false, error: '', client: null };
  },
  computed: {
    ...mapGetters(['currentUser']),
    request() {
      const query = this.$route.query;
      return Object.fromEntries(PARAMS.filter(key => typeof query[key] === 'string').map(key => [key, query[key]]));
    },
    scopes() {
      return (this.request.scope || 'openid').split(' ').filter(Boolean);
    },
  },
  async created() {
    if (!this.request.client_id || !this.request.redirect_uri || !this.request.state) {
      this.error = 'The authorization request is missing client_id, redirect_uri or state.';
      this.loading = false;
      return;
    }
    try {
      this.client = await api.getClientInfo(this.request.client_id);
      if (this.client.is_first_party) {
        await this.decide('approve');
        return;
      }
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },
  methods: {
    describe(scope) {
      return SCOPE_DESCRIPTIONS[scope] || scope;
    },
    async decide(consent) {
      this.deciding = true;
      try {
        // The API validates the redirect against the client's registration
        // and returns where to send the browser (code or access_denied).
        const { redirect_to } = await api.authorizeDecision({
          scope: 'openid', ...this.request, consent,
        });
        window.location.assign(redirect_to);
      } catch (e) {
        this.error = e.message;
        this.loading = false;
        this.deciding = false;
      }
    },
  },
};
</script>

<style scoped>
.scope-list {
  margin: 0;
  padding-left: var(--space-lg);
  color: var(--text-secondary);
  line-height: 1.8;
}
</style>
