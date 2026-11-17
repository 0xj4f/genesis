<template>
  <button type="button" class="btn btn-ghost copy-btn" :class="size === 'sm' ? 'btn-icon copy-sm' : 'btn-sm'"
          :aria-label="label ? undefined : `Copy ${what}`" @click="copy">
    <Check v-if="copied" :size="15" aria-hidden="true" class="copied-icon" />
    <Copy v-else :size="15" aria-hidden="true" />
    <span v-if="label">{{ copied ? 'Copied' : label }}</span>
    <span v-else class="sr-only" aria-live="polite">{{ copied ? 'Copied' : '' }}</span>
  </button>
</template>

<script>
import { Copy, Check } from 'lucide-vue-next';

export default {
  name: 'CopyButton',
  components: { Copy, Check },
  props: {
    value: { type: String, required: true },
    what: { type: String, default: 'value' },
    label: { type: String, default: '' },
    size: { type: String, default: 'sm' },
  },
  data() {
    return { copied: false, timer: null };
  },
  beforeUnmount() { clearTimeout(this.timer); },
  methods: {
    async copy() {
      try {
        await navigator.clipboard.writeText(this.value);
        this.copied = true;
        clearTimeout(this.timer);
        this.timer = setTimeout(() => { this.copied = false; }, 1600);
      } catch {
        /* clipboard unavailable (insecure context); the value stays selectable */
      }
    },
  },
};
</script>

<style scoped>
.copy-sm { width: 32px; min-height: 32px; }
.copied-icon { color: var(--success); }
</style>
