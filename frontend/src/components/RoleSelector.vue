<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const roles = [
  { id: 'employee', label: 'Employee', access: 'General + HR', color: '#1f6feb' },
  { id: 'hr', label: 'HR', access: 'HR policies', color: '#b4237a' },
  { id: 'finance', label: 'Finance', access: 'Finance docs', color: '#047857' },
  { id: 'executive', label: 'Executive', access: 'All departments', color: '#7c3aed' },
]
</script>

<template>
  <div class="role-selector" aria-label="Role selector">
    <button
      v-for="role in roles"
      :key="role.id"
      class="role-option"
      :class="{ active: props.modelValue === role.id }"
      :style="{ '--role-color': role.color }"
      type="button"
      @click="emit('update:modelValue', role.id)"
    >
      <i aria-hidden="true"></i>
      <span>{{ role.label }}</span>
      <small>{{ role.access }}</small>
    </button>
  </div>
</template>

<style scoped>
.role-selector {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.role-option {
  position: relative;
  min-height: 58px;
  border: 1px solid #d8dee7;
  background: #ffffff;
  color: #1e293b;
  border-radius: 6px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  transition:
    transform 150ms ease,
    border-color 150ms ease,
    background 150ms ease;
}

.role-option:hover {
  transform: translateY(-1px);
  border-color: var(--role-color);
}

.role-option i {
  display: block;
  width: 24px;
  height: 4px;
  margin-bottom: 8px;
  border-radius: 999px;
  background: var(--role-color);
}

.role-option span,
.role-option small {
  display: block;
}

.role-option span {
  font-weight: 700;
  font-size: 14px;
}

.role-option small {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.role-option.active {
  border-color: var(--role-color);
  background: color-mix(in srgb, var(--role-color) 11%, #ffffff);
}

@media (max-width: 860px) {
  .role-selector {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
