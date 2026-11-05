<template>
  <div class="token-input" :class="{ focused }" @click="$refs.input.focus()">
    <span v-for="value in modelValue" :key="value" class="token">
      <span class="mono">{{ value }}</span>
      <button type="button" :aria-label="`Remove ${value}`" @click.stop="remove(value)">
        <X :size="13" aria-hidden="true" />
      </button>
    </span>
    <input :id="id" ref="input" v-model="draft" class="token-field" :placeholder="modelValue.length ? '' : placeholder"
           :aria-describedby="describedby || undefined" autocapitalize="none" autocorrect="off" spellcheck="false"
           enterkeyhint="done" @keydown.enter.prevent="add(draft)" @keydown="onKeydown" @blur="onBlur"
           @focus="focused = true" />
  </div>
  <div v-if="remainingSuggestions.length" class="suggestions" role="group" :aria-label="`Suggested ${label}`">
    <button v-for="s in remainingSuggestions" :key="s" type="button" class="chip" @click="add(s)">
      <Plus :size="14" aria-hidden="true" />{{ s }}
    </button>
  </div>
</template>

<script>
import { X, Plus } from 'lucide-vue-next';

// Free-form list input (scopes, audiences): Enter or comma adds, Backspace removes the last value.
export default {
  name: 'TokenInput',
  components: { X, Plus },
  props: {
    modelValue: { type: Array, default: () => [] },
    id: { type: String, required: true },
    label: { type: String, default: 'values' },
    placeholder: { type: String, default: '' },
    suggestions: { type: Array, default: () => [] },
    describedby: { type: String, default: '' },
  },
  emits: ['update:modelValue'],
  data() {
    return { draft: '', focused: false };
  },
  computed: {
    remainingSuggestions() {
      return this.suggestions.filter(s => !this.modelValue.includes(s));
    },
  },
  methods: {
    add(raw) {
      const values = raw.split(/[\s,]+/).map(v => v.trim()).filter(Boolean);
      const next = [...this.modelValue];
      for (const value of values) {
        if (!next.includes(value)) next.push(value.slice(0, 100));
      }
      this.draft = '';
      if (next.length !== this.modelValue.length) this.$emit('update:modelValue', next);
    },
    remove(value) {
      this.$emit('update:modelValue', this.modelValue.filter(v => v !== value));
    },
    onKeydown(event) {
      if (event.key === ',' || event.key === ' ') {
        event.preventDefault();
        this.add(this.draft);
      } else if (event.key === 'Backspace' && !this.draft && this.modelValue.length) {
        this.remove(this.modelValue[this.modelValue.length - 1]);
      }
    },
    onBlur() {
      this.focused = false;
      if (this.draft) this.add(this.draft);
    },
  },
};
</script>

<style scoped>
.token-input {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 44px;
  padding: 6px 8px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  cursor: text;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.token-input.focused { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-soft); }

.token-field {
  flex: 1;
  min-width: 120px;
  min-height: 30px;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--text-base);
}

@media (min-width: 768px) and (pointer: fine) {
  .token-field { font-size: var(--text-md); }
}

.suggestions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
</style>
