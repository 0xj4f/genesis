<template>
  <div class="page-center auth-page">
    <div class="auth-spacer"></div>
    <main class="auth-card" :class="{ wide }">
      <slot />
    </main>
    <div class="auth-spacer"></div>
    <footer class="credit">Genesis IAM · built by 0xj4f</footer>
  </div>
</template>

<script>
// Shared frame for sign-in style pages: a centred card on wide screens,
// edge to edge inside the safe area on phones.
export default {
  name: 'AuthLayout',
  props: { wide: Boolean },
};
</script>

<style scoped>
.auth-page { justify-content: flex-start; }
.auth-spacer { flex: 1; min-height: var(--space-md); }
.auth-card.wide { max-width: 520px; }

.credit {
  margin-top: var(--space-lg);
  font-size: var(--text-xs);
  color: var(--text-subtle);
}
</style>
