<template>
  <dialog ref="dialog" class="sheet" :aria-label="title" @cancel.prevent="$emit('close')" @close="onClose"
          @click="onBackdrop">
    <div class="sheet-panel">
      <header class="sheet-header">
        <button class="btn btn-ghost btn-icon sheet-back" aria-label="Close" @click="$emit('close')">
          <ChevronLeft class="only-mobile" :size="22" aria-hidden="true" />
          <X class="only-desktop" :size="18" aria-hidden="true" />
        </button>
        <h2 class="truncate">{{ title }}</h2>
        <div class="sheet-header-extra"><slot name="header-extra" /></div>
      </header>
      <div class="sheet-body">
        <slot />
      </div>
      <footer v-if="$slots.footer" class="sheet-footer">
        <slot name="footer" />
      </footer>
    </div>
  </dialog>
</template>

<script>
import { ChevronLeft, X } from 'lucide-vue-next';

// Side panel on wide screens, full-screen sheet on phones. The native
// <dialog> traps focus, closes on Esc and keeps the page inert behind it.
export default {
  name: 'AppSheet',
  components: { ChevronLeft, X },
  props: {
    open: Boolean,
    title: { type: String, default: '' },
  },
  emits: ['close'],
  watch: {
    open(value) { this.sync(value); },
  },
  mounted() { this.sync(this.open); },
  beforeUnmount() { document.documentElement.style.overflow = ''; },
  methods: {
    sync(open) {
      const dialog = this.$refs.dialog;
      if (open && !dialog.open) dialog.showModal();
      if (!open && dialog.open) dialog.close();
      document.documentElement.style.overflow = open ? 'hidden' : '';
    },
    // The browser can close the dialog itself (repeated Esc in Chromium).
    onClose() {
      if (this.open) this.$emit('close');
    },
    onBackdrop(event) {
      if (event.target === this.$refs.dialog) this.$emit('close');
    },
  },
};
</script>

<style scoped>
.sheet {
  margin: 0;
  padding: 0;
  border: none;
  width: 100%;
  max-width: 100%;
  height: 100%;
  max-height: 100%;
  background: transparent;
  color: var(--text);
}

.sheet::backdrop { background: var(--overlay); }

.sheet-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

.sheet[open] .sheet-panel { animation: slide-in-up 260ms var(--ease-out); }

@media (min-width: 768px) {
  .sheet { margin-left: auto; width: 520px; }
  .sheet-panel { background: var(--surface); border-left: 1px solid var(--border); box-shadow: var(--shadow-lg); }
  .sheet[open] .sheet-panel { animation: slide-in-right 240ms var(--ease-out); }
}

.sheet-header {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: calc(var(--space-xs) + var(--safe-top)) calc(var(--space-sm) + var(--safe-right)) var(--space-xs) calc(var(--space-xs) + var(--safe-left));
  min-height: calc(var(--topbar-h) + var(--safe-top));
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  flex-shrink: 0;
}

@media (min-width: 768px) {
  .sheet-header { padding: var(--space-sm) var(--space-md) var(--space-sm) var(--space-sm); min-height: var(--topbar-h); }
}

.sheet-header h2 { font-size: var(--text-base); flex: 1; }
.sheet-header-extra { display: flex; gap: var(--space-xs); }

.sheet-body {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: var(--space-lg) calc(var(--space-md) + var(--safe-right)) var(--space-xl) calc(var(--space-md) + var(--safe-left));
}

@media (min-width: 768px) {
  .sheet-body { padding: var(--space-lg); }
}

.sheet-footer {
  flex-shrink: 0;
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md) calc(var(--space-sm) + var(--safe-bottom));
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.only-desktop { display: none; }

@media (min-width: 768px) {
  .only-mobile { display: none; }
  .only-desktop { display: block; }
}

@keyframes slide-in-up { from { transform: translateY(24px); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes slide-in-right { from { transform: translateX(100%); } to { transform: none; } }
</style>
