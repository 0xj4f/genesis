<template>
  <AuthLayout>
    <div v-if="loading" class="status" role="status">
      <span class="spinner status-spinner" aria-hidden="true"></span>
      <h1>Checking the request…</h1>
    </div>

    <div v-else-if="error" class="status">
      <span class="status-icon bad" aria-hidden="true"><CircleAlert :size="24" /></span>
      <h1>Authorization failed</h1>
      <p>{{ error }}</p>
    </div>

    <div v-else class="consent">
      <div class="consent-apps" aria-hidden="true">
        <span class="app-avatar">{{ client.client_name[0].toUpperCase() }}</span>
        <span class="consent-link"><ArrowLeftRight :size="16" /></span>
        <BrandMark large />
      </div>
      <h1><strong>{{ client.client_name }}</strong> wants to access your Genesis account</h1>

      <div class="account-pill">
        <span class="avatar avatar-sm avatar-placeholder">{{ initials }}</span>
        <div class="wrap-anywhere spacer">
          <div class="text-md"><strong>{{ currentUser?.username }}</strong></div>
          <div v-if="currentUser?.email" class="text-sm text-muted truncate">{{ currentUser.email }}</div>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" :disabled="deciding" @click="switchAccount">Not you?</button>
      </div>

      <p class="section-label mt-lg">This will allow {{ client.client_name }} to</p>
      <ul class="scope-list">
        <li v-for="scope in scopes" :key="scope">
          <component :is="scopeIcon(scope)" :size="18" aria-hidden="true" />
          <span>{{ describe(scope) }}</span>
        </li>
      </ul>

      <p class="text-sm text-muted mt-md">You can sign out of this app from your Sessions page at any time.</p>

      <div class="consent-actions">
        <button class="btn btn-secondary btn-lg" :disabled="deciding" @click="decide('deny')">Cancel</button>
        <button class="btn btn-primary btn-lg" :disabled="deciding" @click="decide('approve')">
          <span v-if="deciding" class="spinner" aria-hidden="true"></span>Allow
        </button>
      </div>
    </div>
  </AuthLayout>
</template>

<script>
import { mapGetters } from 'vuex';
import { CircleAlert, ArrowLeftRight, UserRound, Mail, IdCard, RefreshCw, KeyRound } from 'lucide-vue-next';
import api from '@/api';
import AuthLayout from '@/components/ui/AuthLayout.vue';
import BrandMark from '@/components/ui/BrandMark.vue';
import { SCOPE_DESCRIPTIONS } from '@/utils/messages';

const PARAMS = ['response_type', 'client_id', 'redirect_uri', 'scope', 'state', 'nonce', 'code_challenge', 'code_challenge_method'];

export default {
  name: 'ConsentView',
  components: { CircleAlert, ArrowLeftRight, AuthLayout, BrandMark },
  data() {
    return { loading: true, deciding: false, error: '', client: null };
  },
  computed: {
    ...mapGetters(['currentUser', 'initials']),
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
    scopeIcon(scope) {
      return { openid: IdCard, profile: UserRound, email: Mail, offline_access: RefreshCw }[scope] || KeyRound;
    },
    // Sign out, then come back to this same request after signing in again.
    async switchAccount() {
      const back = this.$route.fullPath;
      await this.$store.dispatch('logout');
      this.$router.replace({ path: '/login', query: { next: back } });
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
.consent h1 { font-size: var(--text-xl); font-weight: 400; text-align: center; }
.consent h1 strong { font-weight: 600; }

.consent-apps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.app-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-weight: 600;
  font-size: var(--text-lg);
}

.consent-link { color: var(--text-subtle); display: flex; }

.account-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: var(--space-lg);
  padding: 8px 8px 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-2);
}

.scope-list { list-style: none; display: flex; flex-direction: column; }

.scope-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  font-size: var(--text-md);
}

.scope-list li:last-child { border-bottom: none; }
.scope-list svg { color: var(--text-muted); flex-shrink: 0; }

.consent-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
}
</style>
