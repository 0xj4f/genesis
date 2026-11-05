<template>
  <div class="page-container admin-page">
    <div class="page-header">
      <div>
        <h1>Applications</h1>
        <p>OAuth 2.0 / OpenID Connect clients that use Genesis for sign-in</p>
      </div>
      <router-link v-if="clients.length" to="/admin/applications/new" class="btn btn-primary">
        <Plus :size="16" aria-hidden="true" />New application
      </router-link>
    </div>

    <div v-if="error" class="alert alert-error mb-md" role="alert">
      <CircleAlert :size="18" aria-hidden="true" />
      <div class="spacer">{{ error }}</div>
      <button class="btn btn-secondary btn-sm" @click="load">Retry</button>
    </div>

    <div v-if="loading" class="card card-flush"><SkeletonRows :rows="3" /></div>

    <div v-else-if="!clients.length && !error" class="card">
      <EmptyState title="No applications yet"
                  text="Register an app to let it sign users in with Genesis and request tokens.">
        <template #icon><AppWindow :size="22" /></template>
        <router-link to="/admin/applications/new" class="btn btn-primary">
          <Plus :size="16" aria-hidden="true" />Create application
        </router-link>
      </EmptyState>
    </div>

    <div v-else class="app-grid">
      <article v-for="c in clients" :key="c.id" class="card app-card" :class="{ inactive: !c.is_active }">
        <div class="app-head">
          <span class="app-icon" aria-hidden="true">{{ c.client_name[0].toUpperCase() }}</span>
          <div class="wrap-anywhere spacer">
            <h2><router-link :to="`/admin/applications/${c.id}`" class="app-link">{{ c.client_name }}</router-link></h2>
            <div class="badge-row mt-xs">
              <StatusBadge :label="c.is_active ? 'Active' : 'Inactive'" :tone="c.is_active ? 'success' : 'neutral'" />
              <span class="badge">{{ c.is_confidential ? 'Confidential' : 'Public' }}</span>
              <span v-if="c.is_first_party" class="badge badge-primary">First-party</span>
            </div>
          </div>
          <ChevronRight :size="18" class="list-row-chevron" aria-hidden="true" />
        </div>
        <dl class="dl app-meta">
          <div class="dl-row">
            <dt>Client ID</dt>
            <dd><span class="mono truncate">{{ c.id }}</span><CopyButton class="copy-above" :value="c.id" what="client ID" /></dd>
          </div>
          <div class="dl-row"><dt>Grants</dt><dd class="text-muted">{{ c.grant_types.map(grantLabel).join(', ') }}</dd></div>
          <div class="dl-row">
            <dt>Redirects</dt>
            <dd class="text-muted">{{ c.redirect_uris.length ? `${c.redirect_uris.length} URI${c.redirect_uris.length === 1 ? '' : 's'}` : 'None' }}</dd>
          </div>
        </dl>
      </article>
    </div>
  </div>
</template>

<script>
import { Plus, AppWindow, ChevronRight, CircleAlert } from 'lucide-vue-next';
import api from '@/api';
import SkeletonRows from '@/components/ui/SkeletonRows.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import CopyButton from '@/components/ui/CopyButton.vue';
import { GRANT_TYPES } from '@/utils/oauth';

export default {
  name: 'AdminApplications',
  components: { Plus, AppWindow, ChevronRight, CircleAlert, SkeletonRows, EmptyState, StatusBadge, CopyButton },
  data() {
    return { clients: [], loading: true, error: '' };
  },
  created() {
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      this.error = '';
      try {
        const clients = await api.getClients();
        this.clients = clients.sort((a, b) => Number(b.is_active) - Number(a.is_active)
          || a.client_name.localeCompare(b.client_name));
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    grantLabel(grant) {
      return GRANT_TYPES.find(g => g.value === grant)?.short || grant;
    },
  },
};
</script>

<style scoped>
.app-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--space-md); }

@media (min-width: 900px) {
  .app-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

.app-grid .card + .card { margin-top: 0; }

.app-card {
  position: relative;
  padding: var(--space-md);
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.app-card:hover { border-color: var(--border-strong); }
.app-card:has(.app-link:focus-visible) { outline: 2px solid var(--ring); outline-offset: 2px; }
.app-card.inactive { opacity: 0.75; }

.app-head { display: flex; gap: 12px; align-items: flex-start; }
.app-head h2 { font-size: var(--text-base); }

.app-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-weight: 600;
}

/* The name link covers the card; the copy button sits above it. */
.app-link { color: var(--text); text-decoration: none; }
.app-link::after { content: ''; position: absolute; inset: 0; border-radius: inherit; }
.app-link:focus-visible { outline: none; }
.copy-above { position: relative; z-index: 1; }

.app-meta { margin-top: var(--space-md); border-top: 1px solid var(--border); }
.app-meta .dl-row { font-size: var(--text-sm); padding: 8px 0; }
.app-meta dd { min-width: 0; }
</style>
