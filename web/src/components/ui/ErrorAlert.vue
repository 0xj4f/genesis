<template>
  <div class="alert alert-error" role="alert">
    <CircleAlert :size="18" aria-hidden="true" />
    <div class="spacer">{{ message }}</div>
    <button class="btn btn-secondary btn-sm" @click="$emit('retry')">Retry</button>
  </div>
</template>

<script>
import { CircleAlert } from 'lucide-vue-next';

// A failed load with a Retry button.
export default {
  name: 'ErrorAlert',
  components: { CircleAlert },
  props: { message: { type: String, required: true } },
  emits: ['retry'],
};
</script>
