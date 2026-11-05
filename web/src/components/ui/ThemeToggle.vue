<template>
  <div class="segmented theme-toggle" role="radiogroup" aria-label="Theme">
    <button v-for="option in options" :key="option.value" type="button" role="radio"
            :aria-checked="String(preference === option.value)" :aria-label="option.label"
            :title="option.label" @click="choose(option.value)">
      <component :is="option.icon" :size="15" aria-hidden="true" />
    </button>
  </div>
</template>

<script>
import { Monitor, Sun, Moon } from 'lucide-vue-next';
import { getThemePreference, setThemePreference } from '@/utils/theme';

export default {
  name: 'ThemeToggle',
  data() {
    return {
      preference: getThemePreference(),
      options: [
        { value: 'system', label: 'System theme', icon: Monitor },
        { value: 'light', label: 'Light theme', icon: Sun },
        { value: 'dark', label: 'Dark theme', icon: Moon },
      ],
    };
  },
  methods: {
    choose(value) {
      this.preference = value;
      setThemePreference(value);
    },
  },
};
</script>

<style scoped>
.theme-toggle button { padding: 0; width: 40px; display: inline-flex; align-items: center; justify-content: center; }
</style>
