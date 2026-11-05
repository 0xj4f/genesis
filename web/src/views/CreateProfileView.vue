<template>
  <div class="page-container narrow">
    <div class="page-header">
      <div>
        <h1>Set up your profile</h1>
        <p>Apps you sign in to with Genesis can use this, with your permission.</p>
      </div>
    </div>

    <form class="card stack" novalidate @submit.prevent="handleCreate">
      <ProfileFields v-model="form" names-required />

      <div v-if="error" class="alert alert-error" role="alert">
        <CircleAlert :size="18" aria-hidden="true" /><span>{{ error }}</span>
      </div>

      <div class="actions">
        <button type="submit" class="btn btn-primary btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
          {{ loading ? 'Saving…' : 'Save profile' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import { CircleAlert } from 'lucide-vue-next';
import ProfileFields, { PROFILE_FIELDS } from '@/components/ProfileFields.vue';
import { withoutEmpty } from '@/utils/validation';
import { toast } from '@/utils/feedback';

export default {
  name: 'CreateProfileView',
  components: { CircleAlert, ProfileFields },
  data() {
    return {
      form: Object.fromEntries(PROFILE_FIELDS.map(key => [key, ''])),
      error: '',
      loading: false,
    };
  },
  methods: {
    ...mapActions(['createProfile']),
    async handleCreate() {
      this.error = '';
      if (!this.form.given_name.trim() || !this.form.family_name.trim()) {
        this.error = 'Enter your first and last name.';
        return;
      }
      this.loading = true;
      try {
        // Identity fields (user id, email, sub) are set by the API.
        const payload = {
          ...withoutEmpty(this.form),
          given_name: this.form.given_name,
          family_name: this.form.family_name,
        };
        await this.createProfile(payload);
        toast('Profile saved');
        this.$router.push('/profile');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.narrow { max-width: 640px; }
.actions { display: flex; justify-content: flex-end; }

@media (max-width: 559px) {
  .actions .btn { width: 100%; }
}
</style>
