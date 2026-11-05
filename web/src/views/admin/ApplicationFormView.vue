<template>
  <div class="page-container admin-page form-page">
    <router-link to="/admin/applications" class="back-link">
      <ChevronLeft :size="18" aria-hidden="true" />Applications
    </router-link>

    <div class="page-header">
      <div class="wrap-anywhere">
        <h1>{{ isNew ? 'New application' : (original?.client_name || 'Application') }}</h1>
        <p v-if="isNew">Register an app that signs users in with Genesis.</p>
        <div v-else-if="original" class="badge-row mt-xs">
          <StatusBadge :label="original.is_active ? 'Active' : 'Inactive'" :tone="original.is_active ? 'success' : 'neutral'" />
          <span class="badge">{{ original.is_confidential ? 'Confidential' : 'Public' }}</span>
          <span v-if="original.is_first_party" class="badge badge-primary">First-party</span>
        </div>
      </div>
    </div>

    <div v-if="loadError" class="alert alert-error" role="alert">
      <CircleAlert :size="18" aria-hidden="true" />
      <div class="spacer">{{ loadError }}</div>
      <button class="btn btn-secondary btn-sm" @click="load">Retry</button>
    </div>

    <div v-else-if="loading" class="card stack" aria-busy="true">
      <span class="skeleton" style="height: 14px; width: 30%;"></span>
      <span class="skeleton" style="height: 40px;"></span>
      <span class="skeleton" style="height: 14px; width: 40%;"></span>
      <span class="skeleton" style="height: 80px;"></span>
    </div>

    <form v-else class="stack" novalidate @submit.prevent="save">
      <!-- Credentials (existing apps) -->
      <section v-if="!isNew" class="card">
        <div class="card-header">
          <h2>Credentials</h2>
          <p>Use these in your app's OAuth configuration.</p>
        </div>
        <div class="form-group">
          <span class="form-label">Client ID</span>
          <div class="secret-box">
            <code class="mono wrap-anywhere">{{ original.id }}</code>
            <CopyButton :value="original.id" what="client ID" />
          </div>
        </div>
        <div class="form-group mt-md">
          <span class="form-label">Client secret</span>
          <div class="secret-row">
            <span class="text-muted text-md">Hidden. Secrets are shown only once, when created or rotated.</span>
            <button type="button" class="btn btn-secondary btn-sm" :disabled="busy" @click="rotate">
              <RefreshCw :size="15" aria-hidden="true" />Rotate secret
            </button>
          </div>
        </div>
      </section>

      <!-- Basics -->
      <section class="card">
        <div class="card-header"><h2>Basics</h2></div>
        <div class="stack">
          <div class="form-group">
            <label for="client-name">Name</label>
            <input id="client-name" v-model.trim="form.client_name" class="form-input" maxlength="100" required
                   placeholder="e.g. Customer portal" :aria-invalid="errors.client_name ? 'true' : undefined"
                   aria-describedby="client-name-msg" />
            <p id="client-name-msg" :class="errors.client_name ? 'form-error' : 'form-hint'">
              {{ errors.client_name || 'Shown to users on the consent screen.' }}
            </p>
          </div>

          <fieldset class="form-group">
            <legend class="form-label">Application type</legend>
            <div class="radio-cards mt-xs">
              <label class="radio-card" :class="{ locked: !isNew }">
                <input v-model="form.is_confidential" type="radio" :value="true" :disabled="!isNew" />
                <div><strong>Server-side app</strong><span>Confidential. Runs on a server that can keep a secret.</span></div>
              </label>
              <label class="radio-card" :class="{ locked: !isNew }">
                <input v-model="form.is_confidential" type="radio" :value="false" :disabled="!isNew" />
                <div><strong>SPA or mobile app</strong><span>Public. Runs on the user's device; uses PKCE, no secret.</span></div>
              </label>
            </div>
            <p v-if="!isNew" class="form-hint">The type can't be changed after the app is created.</p>
          </fieldset>
        </div>
      </section>

      <!-- Sign-in -->
      <section class="card">
        <div class="card-header">
          <h2>Redirect URIs</h2>
          <p>Where Genesis may send users back after sign-in. Must match exactly.</p>
        </div>
        <div class="stack-sm">
          <div v-for="(uri, i) in form.redirect_uris" :key="i" class="form-group">
            <label :for="`redirect-${i}`" class="sr-only">Redirect URI {{ i + 1 }}</label>
            <div class="row uri-row">
              <input :id="`redirect-${i}`" v-model.trim="form.redirect_uris[i]" type="url" inputmode="url"
                     class="form-input mono-input" placeholder="https://app.example.com/callback"
                     autocapitalize="none" autocorrect="off" spellcheck="false"
                     :aria-invalid="uriErrors[i] ? 'true' : undefined" :aria-describedby="`redirect-${i}-msg`"
                     @blur="touched.uris = true" />
              <button type="button" class="btn btn-ghost btn-icon" :aria-label="`Remove redirect URI ${i + 1}`"
                      @click="removeUri(i)">
                <Trash2 :size="16" aria-hidden="true" />
              </button>
            </div>
            <p v-if="uriErrors[i]" :id="`redirect-${i}-msg`" class="form-error">{{ uriErrors[i] }}</p>
          </div>
          <div>
            <button type="button" class="btn btn-secondary btn-sm" :disabled="form.redirect_uris.length >= 50" @click="addUri">
              <Plus :size="15" aria-hidden="true" />Add redirect URI
            </button>
          </div>
          <p v-if="errors.redirect_uris" class="form-error">{{ errors.redirect_uris }}</p>
        </div>
      </section>

      <!-- Access -->
      <section class="card">
        <div class="card-header">
          <h2>Access</h2>
          <p>What the app may request.</p>
        </div>
        <div class="stack">
          <div class="form-group">
            <label for="scopes">Allowed scopes</label>
            <TokenInput id="scopes" v-model="form.allowed_scopes" label="scopes" :suggestions="scopeSuggestions"
                        placeholder="Add a scope" describedby="scopes-hint" />
            <p id="scopes-hint" class="form-hint">Requests for any other scope are rejected.</p>
          </div>
          <div class="form-group">
            <label for="audiences">Allowed audiences</label>
            <TokenInput id="audiences" v-model="form.allowed_audiences" label="audiences"
                        placeholder="e.g. orders-api" describedby="audiences-hint" />
            <p id="audiences-hint" class="form-hint">APIs this app's tokens are valid for, in addition to the default audience.</p>
          </div>
          <fieldset class="form-group">
            <legend class="form-label">Grant types</legend>
            <div class="stack-sm mt-xs">
              <label v-for="g in grantOptions" :key="g.value" class="check grant" :class="{ disabled: g.disabled }">
                <input v-model="form.grant_types" type="checkbox" :value="g.value" :disabled="g.disabled" />
                <span><strong>{{ g.label }}</strong><span class="form-hint">{{ g.hint }}</span></span>
              </label>
            </div>
            <p v-if="errors.grant_types" class="form-error">{{ errors.grant_types }}</p>
          </fieldset>
          <div class="toggle-row">
            <div>
              <label for="first-party" class="form-label">First-party application</label>
              <p class="form-hint">Skips the consent screen. Only for apps you operate yourself.</p>
            </div>
            <input id="first-party" v-model="form.is_first_party" type="checkbox" class="switch" role="switch" />
          </div>
        </div>
      </section>

      <!-- Danger zone -->
      <section v-if="!isNew" class="card danger-card">
        <div class="card-header"><h2 class="text-danger">{{ original.is_active ? 'Deactivate application' : 'Reactivate application' }}</h2></div>
        <div class="danger-row">
          <p class="text-muted text-md">
            {{ original.is_active
              ? 'Stops new sign-ins and token requests from this app. You can reactivate it later.'
              : 'Allow this app to sign users in and request tokens again.' }}
          </p>
          <button type="button" class="btn btn-sm" :class="original.is_active ? 'btn-danger-outline' : 'btn-secondary'"
                  :disabled="busy" @click="toggleActive">
            {{ original.is_active ? 'Deactivate' : 'Reactivate' }}
          </button>
        </div>
      </section>

      <div v-if="saveError" class="alert alert-error" role="alert">
        <CircleAlert :size="18" aria-hidden="true" />{{ saveError }}
      </div>

      <div class="form-actions">
        <router-link to="/admin/applications" class="btn btn-secondary">Cancel</router-link>
        <button type="submit" class="btn btn-primary" :disabled="busy || (!isNew && !dirty)">
          <span v-if="busy" class="spinner" aria-hidden="true"></span>
          {{ isNew ? 'Create application' : 'Save changes' }}
        </button>
      </div>
    </form>

    <SecretRevealDialog :secret="reveal.secret" :client-id="reveal.clientId" :client-name="reveal.clientName"
                        :heading="reveal.heading" @close="onRevealClosed" />
  </div>
</template>

<script>
import { ChevronLeft, CircleAlert, Plus, Trash2, RefreshCw } from 'lucide-vue-next';
import api from '@/api';
import CopyButton from '@/components/ui/CopyButton.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import TokenInput from '@/components/ui/TokenInput.vue';
import SecretRevealDialog from '@/components/admin/SecretRevealDialog.vue';
import { SCOPE_DESCRIPTIONS } from '@/utils/messages';
import { GRANT_TYPES, redirectUriError } from '@/utils/oauth';
import { toast, confirmAction } from '@/utils/feedback';

const EDITABLE = ['client_name', 'redirect_uris', 'allowed_scopes', 'allowed_audiences', 'grant_types', 'is_first_party'];

function blankForm() {
  return {
    client_name: '',
    is_confidential: true,
    redirect_uris: [''],
    allowed_scopes: ['openid', 'profile', 'email', 'offline_access'],
    allowed_audiences: [],
    grant_types: ['authorization_code', 'refresh_token'],
    is_first_party: false,
  };
}

function toPayload(form) {
  return {
    ...form,
    redirect_uris: form.redirect_uris.map(u => u.trim()).filter(Boolean),
  };
}

export default {
  name: 'ApplicationForm',
  components: { ChevronLeft, CircleAlert, Plus, Trash2, RefreshCw, CopyButton, StatusBadge, TokenInput, SecretRevealDialog },
  data() {
    return {
      original: null,
      form: blankForm(),
      loading: false,
      loadError: '',
      saveError: '',
      busy: false,
      submitted: false,
      touched: { uris: false },
      leaving: false,
      reveal: { secret: '', clientId: '', clientName: '', heading: '', next: null },
    };
  },
  computed: {
    isNew() { return !this.$route.params.id; },
    scopeSuggestions() { return Object.keys(SCOPE_DESCRIPTIONS); },
    grantOptions() {
      return GRANT_TYPES.map(g => ({ ...g, disabled: g.confidentialOnly && !this.form.is_confidential }));
    },
    uriErrors() {
      if (!this.submitted && !this.touched.uris) return [];
      return this.form.redirect_uris.map(uri => (uri ? redirectUriError(uri) : ''));
    },
    errors() {
      if (!this.submitted) return {};
      const errors = {};
      if (!this.form.client_name) errors.client_name = 'Enter a name for the application.';
      const uris = this.form.redirect_uris.filter(Boolean);
      if (this.form.grant_types.includes('authorization_code') && !uris.length) {
        errors.redirect_uris = 'Add at least one redirect URI for the authorization code grant.';
      }
      if (!this.form.grant_types.length) errors.grant_types = 'Choose at least one grant type.';
      return errors;
    },
    valid() {
      return !Object.keys(this.errors).length && !this.uriErrors.some(Boolean);
    },
    dirty() {
      const current = toPayload(this.form);
      if (this.isNew) return JSON.stringify(current) !== JSON.stringify(toPayload(blankForm()));
      if (!this.original) return false;
      return EDITABLE.some(key => JSON.stringify(current[key]) !== JSON.stringify(this.original[key]));
    },
  },
  watch: {
    // Public clients cannot hold a secret, so client credentials does not apply.
    'form.is_confidential'(confidential) {
      if (!confidential) this.form.grant_types = this.form.grant_types.filter(g => g !== 'client_credentials');
    },
    '$route.params.id'() { this.load(); },
  },
  created() {
    this.load();
  },
  async beforeRouteLeave() {
    if (this.leaving || !this.dirty || this.reveal.secret) return true;
    return confirmAction({
      title: 'Discard unsaved changes?',
      message: 'Your edits to this application will be lost.',
      confirmLabel: 'Discard',
      danger: true,
    });
  },
  methods: {
    async load() {
      this.leaving = false;
      this.submitted = false;
      this.touched.uris = false;
      this.saveError = '';
      if (this.isNew) {
        this.original = null;
        this.form = blankForm();
        return;
      }
      this.loading = true;
      this.loadError = '';
      try {
        this.setOriginal(await api.getClient(this.$route.params.id));
      } catch (e) {
        this.loadError = e.message;
      } finally {
        this.loading = false;
      }
    },
    setOriginal(client) {
      this.original = client;
      this.form = {
        client_name: client.client_name,
        is_confidential: client.is_confidential,
        redirect_uris: client.redirect_uris.length ? [...client.redirect_uris] : [''],
        allowed_scopes: [...client.allowed_scopes],
        allowed_audiences: [...client.allowed_audiences],
        grant_types: [...client.grant_types],
        is_first_party: client.is_first_party,
      };
    },
    addUri() {
      this.form.redirect_uris.push('');
      this.$nextTick(() => document.getElementById(`redirect-${this.form.redirect_uris.length - 1}`)?.focus());
    },
    removeUri(index) {
      this.form.redirect_uris.splice(index, 1);
      if (!this.form.redirect_uris.length) this.form.redirect_uris.push('');
    },
    focusFirstError() {
      this.$nextTick(() => document.querySelector('.form-page [aria-invalid="true"]')?.focus());
    },
    async save() {
      this.submitted = true;
      this.saveError = '';
      if (!this.valid) {
        this.focusFirstError();
        return;
      }
      this.busy = true;
      try {
        const payload = toPayload(this.form);
        if (this.isNew) {
          const created = await api.createClient(payload);
          this.leaving = true;
          this.reveal = {
            secret: created.client_secret, clientId: created.id, clientName: created.client_name,
            heading: 'Application created', next: `/admin/applications/${created.id}`,
          };
        } else {
          const update = Object.fromEntries(EDITABLE.map(key => [key, payload[key]]));
          this.setOriginal(await api.updateClient(this.original.id, update));
          toast('Application saved');
        }
      } catch (e) {
        this.saveError = e.message;
      } finally {
        this.busy = false;
      }
    },
    async rotate() {
      const ok = await confirmAction({
        title: `Rotate the secret for ${this.original.client_name}?`,
        message: 'The current secret stops working immediately. Update the app with the new secret right away.',
        confirmLabel: 'Rotate secret',
        danger: true,
      });
      if (!ok) return;
      this.busy = true;
      try {
        const res = await api.rotateClientSecret(this.original.id);
        this.reveal = { secret: res.client_secret, clientId: String(res.client_id), clientName: res.client_name,
          heading: 'New client secret', next: null };
      } catch (e) {
        this.saveError = e.message;
      } finally {
        this.busy = false;
      }
    },
    async toggleActive() {
      const deactivating = this.original.is_active;
      const ok = await confirmAction({
        title: `${deactivating ? 'Deactivate' : 'Reactivate'} ${this.original.client_name}?`,
        message: deactivating ? 'Users can no longer sign in to this app with Genesis.' : 'The app can sign users in again.',
        confirmLabel: deactivating ? 'Deactivate' : 'Reactivate',
        danger: deactivating,
      });
      if (!ok) return;
      this.busy = true;
      try {
        const updated = await api.updateClient(this.original.id, { is_active: !deactivating });
        this.original = updated;
        toast(deactivating ? 'Application deactivated' : 'Application reactivated');
      } catch (e) {
        this.saveError = e.message;
      } finally {
        this.busy = false;
      }
    },
    onRevealClosed() {
      const next = this.reveal.next;
      this.reveal = { secret: '', clientId: '', clientName: '', heading: '', next: null };
      if (next) {
        toast('Application created');
        this.$router.replace(next);
      }
    },
  },
};
</script>

<style scoped>
.form-page { max-width: 760px; }

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  min-height: 44px;
  margin: calc(-1 * var(--space-sm)) 0 var(--space-xs) -6px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: var(--text-md);
}

.back-link:hover { color: var(--text); }

.card + .card { margin-top: 0; }

fieldset { border: none; }

.secret-box {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 8px 6px 8px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.secret-box code { flex: 1; font-size: var(--text-sm); }

.secret-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.radio-card.locked { cursor: default; }
.radio-card.locked:not(:has(input:checked)) { opacity: 0.5; }

.uri-row { gap: var(--space-xs); }
.mono-input { font-family: var(--font-mono); font-size: var(--text-base); }

@media (min-width: 768px) and (pointer: fine) {
  .mono-input { font-size: var(--text-sm); }
}

.grant > span { display: flex; flex-direction: column; gap: 2px; }
.grant strong { font-weight: 500; }
.grant.disabled { opacity: 0.5; cursor: not-allowed; }

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border);
}

.danger-card { border-color: color-mix(in srgb, var(--danger) 35%, transparent); }
.danger-card .card-header h2 { font-size: var(--text-base); }

.danger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}

/* Save bar stays reachable above the tab bar on phones. */
.form-actions {
  position: sticky;
  bottom: calc(var(--tabbar-h) + var(--safe-bottom));
  z-index: 5;
  display: flex;
  gap: var(--space-sm);
  justify-content: flex-end;
  margin: 0 calc(-1 * var(--space-md));
  padding: var(--space-sm) var(--space-md);
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--border);
}

.form-actions .btn { flex: 1; }

@media (min-width: 640px) {
  .form-actions .btn { flex: none; }
}

@media (min-width: 1024px) {
  .form-actions { bottom: 0; margin: 0; padding: var(--space-md) 0; border-top: none; background: none; backdrop-filter: none; -webkit-backdrop-filter: none; }
}
</style>
