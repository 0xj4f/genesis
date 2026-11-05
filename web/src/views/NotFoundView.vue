<template>
  <AuthLayout>
    <div class="status">
      <span class="status-icon" aria-hidden="true"><Compass :size="24" /></span>
      <p class="code tabular">404</p>
      <h1>Page not found</h1>
      <p>There's nothing at this address. Check the link or head back.</p>
      <router-link to="/" class="btn btn-primary btn-block btn-lg mt-lg">Go to Genesis</router-link>
    </div>
  </AuthLayout>
</template>

<script>
import { Compass } from 'lucide-vue-next';
import AuthLayout from '@/components/ui/AuthLayout.vue';

export default {
  name: 'NotFoundView',
  components: { Compass, AuthLayout },
};
</script>

<style scoped>
.status .code { margin: 0 0 var(--space-xs); font-size: var(--text-sm); font-weight: 600; color: var(--text-subtle); }
</style>
