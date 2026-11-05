<template>
  <div class="empty">
    <div class="empty-icon" aria-hidden="true"><slot name="icon" /></div>
    <h3>{{ title }}</h3>
    <p v-if="text">{{ text }}</p>
    <div v-if="$slots.default" class="empty-action"><slot /></div>
  </div>
</template>

<script>
export default {
  name: 'EmptyState',
  props: {
    title: { type: String, required: true },
    text: { type: String, default: '' },
  },
};
</script>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--space-2xl) var(--space-lg);
}

.empty-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-md);
}

.empty-icon:empty { display: none; }
.empty h3 { font-size: var(--text-base); }
.empty p { color: var(--text-muted); font-size: var(--text-md); margin-top: var(--space-xs); max-width: 36ch; }
.empty-action { margin-top: var(--space-md); }
</style>
