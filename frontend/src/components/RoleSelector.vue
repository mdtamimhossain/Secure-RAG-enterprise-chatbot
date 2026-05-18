<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const roles = [
  { id: 'employee', label: 'Employee', access: 'General + HR' },
  { id: 'hr', label: 'HR', access: 'HR policies' },
  { id: 'finance', label: 'Finance', access: 'Finance docs' },
  { id: 'executive', label: 'Executive', access: 'All departments' },
]
</script>

<template>
  <div class="role-selector" aria-label="Role selector">
    <button
      v-for="role in roles"
      :key="role.id"
      class="role-option"
      :class="{ active: props.modelValue === role.id }"
      type="button"
      @click="emit('update:modelValue', role.id)"
    >
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
  min-height: 58px;
  border: 1px solid #d8dee7;
  background: #ffffff;
  color: #1e293b;
  border-radius: 6px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
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
  border-color: #1f6feb;
  background: #eef6ff;
}

@media (max-width: 860px) {
  .role-selector {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
