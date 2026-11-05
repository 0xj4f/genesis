<template>
  <span class="brand-mark" :class="{ 'brand-mark-lg': large }" aria-hidden="true">
    <svg :width="large ? 24 : 18" :height="large ? 24 : 18" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 3 4.5 6v5.5c0 4.6 3.1 8.4 7.5 9.5 4.4-1.1 7.5-4.9 7.5-9.5V6L12 3Z" />
      <path d="M9 12.2 11.2 14.4 15.2 10" />
    </svg>
  </span>
</template>

<script>
export default {
  name: 'BrandMark',
  props: { large: Boolean },
};
</script>
