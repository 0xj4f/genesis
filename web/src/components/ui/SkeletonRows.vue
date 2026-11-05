<template>
  <div class="skeleton-rows" aria-busy="true" aria-label="Loading">
    <div v-for="n in rows" :key="n" class="sk-row">
      <span v-if="avatar" class="skeleton sk-avatar"></span>
      <div class="sk-lines">
        <span class="skeleton sk-line" :style="{ width: `${40 + ((n * 17) % 35)}%` }"></span>
        <span class="skeleton sk-line sk-sub" :style="{ width: `${25 + ((n * 23) % 30)}%` }"></span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SkeletonRows',
  props: {
    rows: { type: Number, default: 5 },
    avatar: { type: Boolean, default: true },
  },
};
</script>

<style scoped>
.sk-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px var(--space-md);
  min-height: 64px;
  border-bottom: 1px solid var(--border);
}

.sk-row:last-child { border-bottom: none; }
.sk-avatar { width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0; }
.sk-lines { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.sk-line { height: 12px; }
.sk-sub { height: 10px; }
</style>
