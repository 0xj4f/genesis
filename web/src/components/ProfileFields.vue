<template>
  <div class="stack">
    <fieldset class="stack">
      <legend class="section-label">Personal</legend>
      <div class="grid-2">
        <div class="form-group">
          <label for="pf-given">First name<span v-if="namesRequired" aria-hidden="true"> *</span></label>
          <input id="pf-given" :value="modelValue.given_name" class="form-input" autocomplete="given-name"
                 :required="namesRequired" maxlength="100" @input="set('given_name', $event)" />
        </div>
        <div class="form-group">
          <label for="pf-family">Last name<span v-if="namesRequired" aria-hidden="true"> *</span></label>
          <input id="pf-family" :value="modelValue.family_name" class="form-input" autocomplete="family-name"
                 :required="namesRequired" maxlength="100" @input="set('family_name', $event)" />
        </div>
      </div>
      <div class="form-group">
        <label for="pf-nick">Nickname <span class="text-subtle">(optional)</span></label>
        <input id="pf-nick" :value="modelValue.nick_name" class="form-input" autocomplete="nickname"
               @input="set('nick_name', $event)" />
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label for="pf-dob">Date of birth</label>
          <input id="pf-dob" :value="modelValue.date_of_birth" type="date" class="form-input" autocomplete="bday"
                 @input="set('date_of_birth', $event)" />
        </div>
        <div class="form-group">
          <label for="pf-mobile">Mobile</label>
          <input id="pf-mobile" :value="modelValue.mobile_number" type="tel" inputmode="tel" class="form-input"
                 placeholder="+1 555 123 4567" autocomplete="tel" @input="set('mobile_number', $event)" />
        </div>
      </div>
    </fieldset>

    <fieldset class="stack">
      <legend class="section-label">Address</legend>
      <div class="form-group">
        <label for="pf-line1">Street address</label>
        <input id="pf-line1" :value="modelValue.address_line1" class="form-input" autocomplete="address-line1"
               @input="set('address_line1', $event)" />
      </div>
      <div class="form-group">
        <label for="pf-line2">Apartment, suite, etc. <span class="text-subtle">(optional)</span></label>
        <input id="pf-line2" :value="modelValue.address_line2" class="form-input" autocomplete="address-line2"
               @input="set('address_line2', $event)" />
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label for="pf-city">City</label>
          <input id="pf-city" :value="modelValue.city" class="form-input" autocomplete="address-level2"
                 @input="set('city', $event)" />
        </div>
        <div class="form-group">
          <label for="pf-state">State / region</label>
          <input id="pf-state" :value="modelValue.state" class="form-input" autocomplete="address-level1"
                 @input="set('state', $event)" />
        </div>
        <div class="form-group">
          <label for="pf-zip">Postal code</label>
          <input id="pf-zip" :value="modelValue.zip_code" class="form-input" autocomplete="postal-code"
                 @input="set('zip_code', $event)" />
        </div>
        <div class="form-group">
          <label for="pf-country">Country</label>
          <input id="pf-country" :value="modelValue.country" class="form-input" autocomplete="country-name"
                 @input="set('country', $event)" />
        </div>
      </div>
    </fieldset>
  </div>
</template>

<script>
export const PROFILE_FIELDS = [
  'given_name', 'family_name', 'nick_name', 'date_of_birth', 'mobile_number',
  'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country',
];

// Shared by profile creation and editing.
export default {
  name: 'ProfileFields',
  props: {
    modelValue: { type: Object, required: true },
    namesRequired: Boolean,
  },
  emits: ['update:modelValue'],
  methods: {
    set(key, event) {
      this.$emit('update:modelValue', { ...this.modelValue, [key]: event.target.value });
    },
  },
};
</script>

<style scoped>
fieldset { border: none; }
.grid-2 { display: grid; gap: var(--space-md); }

@media (min-width: 560px) {
  .grid-2 { grid-template-columns: 1fr 1fr; }
}
</style>
