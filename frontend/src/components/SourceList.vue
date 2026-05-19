<script setup>
import { computed } from 'vue'
import { FileText, Library, ShieldCheck } from '@lucide/vue'

const props = defineProps({
  sources: {
    type: Array,
    default: () => [],
  },
})

const sourceCountLabel = computed(() =>
  props.sources.length === 1 ? '1 reference' : `${props.sources.length} references`,
)

function labelFor(source) {
  const metadata = source.metadata || {}
  return metadata.filename || metadata.source || 'Company document'
}
</script>

<template>
  <section class="reference-panel" aria-label="Answer references">
    <div class="reference-heading">
      <div class="reference-icon">
        <Library :size="18" aria-hidden="true" />
      </div>
      <div>
        <h2>References</h2>
        <p>{{ sourceCountLabel }} from authorized retrieval</p>
      </div>
    </div>

    <div v-if="sources.length === 0" class="empty-reference">
      <ShieldCheck :size="22" aria-hidden="true" />
      <p>References will appear here after the assistant retrieves matching company chunks.</p>
    </div>

    <ol v-else class="reference-list">
      <li v-for="(source, index) in sources" :key="`${labelFor(source)}-${index}`" class="reference-card">
        <div class="reference-title">
          <span>{{ index + 1 }}</span>
          <div>
            <strong>{{ labelFor(source) }}</strong>
            <small>{{ source.metadata?.department || 'general' }} / {{ source.metadata?.category || 'general' }}</small>
          </div>
          <FileText :size="16" aria-hidden="true" />
        </div>
        <p>{{ source.content }}</p>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.reference-panel {
  min-width: 0;
  color: var(--text, #172033);
}

.reference-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border, #e5eaf0);
}

.reference-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 10px;
  background: color-mix(in srgb, var(--role-accent) 12%, var(--surface, #ffffff));
  color: var(--role-accent);
}

h2,
p {
  margin: 0;
}

h2 {
  color: var(--text, #172033);
  font-size: 16px;
}

.reference-heading p {
  margin-top: 3px;
  color: var(--muted, #64748b);
  font-size: 12px;
}

.empty-reference {
  display: grid;
  place-items: center;
  min-height: 230px;
  padding: 22px;
  color: var(--muted, #64748b);
  text-align: center;
}

.empty-reference svg {
  color: var(--role-accent);
}

.empty-reference p {
  margin-top: 10px;
  max-width: 260px;
  font-size: 13px;
  line-height: 1.55;
}

.reference-list {
  display: grid;
  gap: 10px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.reference-card {
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  background: var(--surface, #ffffff);
  padding: 12px;
  animation: referenceIn 180ms ease both;
}

.reference-title {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 18px;
  gap: 9px;
  align-items: start;
}

.reference-title > span {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  background: var(--text, #111827);
  color: var(--surface, #ffffff);
  font-size: 12px;
  font-weight: 850;
}

.reference-title strong,
.reference-title small {
  display: block;
}

.reference-title strong {
  overflow: hidden;
  color: var(--text, #172033);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reference-title small {
  margin-top: 2px;
  color: var(--muted, #64748b);
  font-size: 11px;
  text-transform: capitalize;
}

.reference-title svg {
  color: var(--muted, #64748b);
}

.reference-card p {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 10px;
  color: var(--muted, #475569);
  font-size: 13px;
  line-height: 1.5;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
}

@keyframes referenceIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
