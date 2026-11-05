<template>
  <span class="badge" :class="toneClass"><span class="dot" aria-hidden="true"></span>{{ label }}</span>
</template>

<script>
const TONES = { success: 'badge-success', danger: 'badge-danger', warning: 'badge-warning', neutral: '' };

// Status with a dot and a text label, so colour is never the only signal.
export default {
  name: 'StatusBadge',
  props: {
    label: { type: String, required: true },
    tone: { type: String, default: 'neutral' },
  },
  computed: {
    toneClass() { return TONES[this.tone] ?? ''; },
  },
};
</script>
