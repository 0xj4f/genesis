<template>
  <div class="input-wrap">
    <input :id="id" :value="modelValue" :type="visible ? 'text' : 'password'" class="form-input"
           :autocomplete="autocomplete" :placeholder="placeholder" :required="required"
           :aria-invalid="invalid ? 'true' : undefined" :aria-describedby="describedby || undefined"
           autocapitalize="none" autocorrect="off" spellcheck="false"
           @input="$emit('update:modelValue', $event.target.value)" @blur="$emit('blur')" />
    <button type="button" class="input-trailing" :aria-label="visible ? 'Hide password' : 'Show password'"
            :aria-pressed="String(visible)" @click="visible = !visible">
      <EyeOff v-if="visible" :size="18" aria-hidden="true" />
      <Eye v-else :size="18" aria-hidden="true" />
    </button>
  </div>
</template>

<script>
import { Eye, EyeOff } from 'lucide-vue-next';

export default {
  name: 'PasswordInput',
  components: { Eye, EyeOff },
  props: {
    modelValue: { type: String, default: '' },
    id: { type: String, required: true },
    autocomplete: { type: String, default: 'current-password' },
    placeholder: { type: String, default: '' },
    required: Boolean,
    invalid: Boolean,
    describedby: { type: String, default: '' },
  },
  emits: ['update:modelValue', 'blur'],
  data() {
    return { visible: false };
  },
};
</script>
