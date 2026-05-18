<script setup>
import { FileText, ShieldCheck } from '@lucide/vue'

defineProps({
  sources: {
    type: Array,
    default: () => [],
  },
})

function labelFor(source) {
  const metadata = source.metadata || {}
  return metadata.filename || metadata.source || 'Unknown source'
}
</script>

<template>
  <section class="sources-panel" aria-label="Retrieved sources">
    <div class="panel-heading">
      <div>
        <h2>Retrieved Sources</h2>
        <p>{{ sources.length }} document chunks used</p>
      </div>
      <ShieldCheck :size="20" aria-hidden="true" />
    </div>

    <div v-if="sources.length === 0" class="empty-state">
      No sources returned for this answer.
    </div>

    <ol v-else class="source-list">
      <li v-for="(source, index) in sources" :key="`${labelFor(source)}-${index}`" class="source-item">
        <div class="source-title">
          <FileText :size="16" aria-hidden="true" />
          <span>{{ labelFor(source) }}</span>
        </div>
        <dl>
          <div>
            <dt>Department</dt>
            <dd>{{ source.metadata?.department || 'general' }}</dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{{ source.metadata?.category || 'general' }}</dd>
          </div>
        </dl>
        <p>{{ source.content }}</p>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.sources-panel {
  min-width: 0;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5eaf0;
}

h2 {
  margin: 0;
  color: #172033;
  font-size: 16px;
}

p {
  margin: 0;
}

.panel-heading p {
  margin-top: 3px;
  color: #64748b;
  font-size: 13px;
}

.empty-state {
  padding: 18px 0;
  color: #64748b;
  font-size: 14px;
}

.source-list {
  display: grid;
  gap: 12px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.source-item {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  background: #ffffff;
}

.source-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #172033;
  font-weight: 700;
  font-size: 13px;
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 10px 0;
}

dt {
  color: #64748b;
  font-size: 11px;
  text-transform: uppercase;
}

dd {
  margin: 2px 0 0;
  color: #334155;
  font-size: 13px;
}

.source-item p {
  display: -webkit-box;
  overflow: hidden;
  color: #475569;
  font-size: 13px;
  line-height: 1.45;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
}
</style>
