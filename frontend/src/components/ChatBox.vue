<script setup>
import { computed, ref } from 'vue'
import { Bot, Send, UserRound, Trash2 } from '@lucide/vue'
import { sendChatMessage } from '../services/api'

const props = defineProps({
  role: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['sources-updated'])

const question = ref('')
const loading = ref(false)
const error = ref('')
const messages = ref([
  {
    sender: 'assistant',
    text: 'Ask about policies, benefits, leave, handbooks, or department documents available to your role.',
  },
])

const canSend = computed(() => question.value.trim().length > 0 && !loading.value)

async function submitQuestion() {
  if (!canSend.value) return

  const currentQuestion = question.value.trim()
  question.value = ''
  error.value = ''
  messages.value.push({ sender: 'user', text: currentQuestion })
  loading.value = true

  try {
    const response = await sendChatMessage({
      question: currentQuestion,
      role: props.role,
    })

    messages.value.push({
      sender: 'assistant',
      text: response.answer,
    })
    emit('sources-updated', response.sources || [])
  } catch (err) {
    error.value = err.message
    emit('sources-updated', [])
  } finally {
    loading.value = false
  }
}

function clearChat() {
  messages.value = [
    {
      sender: 'assistant',
      text: 'Ask about policies, benefits, leave, handbooks, or department documents available to your role.',
    },
  ]
  emit('sources-updated', [])
  error.value = ''
}
</script>

<template>
  <section class="chat-panel" aria-label="AI assistant chat">
    <div class="chat-header">
      <div>
        <h2>Internal AI Assistant</h2>
        <p>Role context: {{ role }}</p>
      </div>
      <button class="icon-button" type="button" title="Clear chat" @click="clearChat">
        <Trash2 :size="18" aria-hidden="true" />
      </button>
    </div>

    <div class="message-list" aria-live="polite">
      <article
        v-for="(message, index) in messages"
        :key="index"
        class="message"
        :class="message.sender"
      >
        <div class="avatar" aria-hidden="true">
          <Bot v-if="message.sender === 'assistant'" :size="17" />
          <UserRound v-else :size="17" />
        </div>
        <p>{{ message.text }}</p>
      </article>
      <article v-if="loading" class="message assistant">
        <div class="avatar" aria-hidden="true">
          <Bot :size="17" />
        </div>
        <p>Searching authorized documents...</p>
      </article>
    </div>

    <p v-if="error" class="error-message">{{ error }}</p>

    <form class="composer" @submit.prevent="submitQuestion">
      <textarea
        v-model="question"
        rows="3"
        placeholder="Ask a question about company policies or department documents"
      />
      <button type="submit" :disabled="!canSend" title="Send question">
        <Send :size="18" aria-hidden="true" />
        <span>Send</span>
      </button>
    </form>
  </section>
</template>

<style scoped>
.chat-panel {
  display: grid;
  min-height: 620px;
  grid-template-rows: auto 1fr auto auto;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5eaf0;
}

h2,
p {
  margin: 0;
}

h2 {
  color: #172033;
  font-size: 17px;
}

.chat-header p {
  margin-top: 3px;
  color: #64748b;
  font-size: 13px;
  text-transform: capitalize;
}

.icon-button {
  display: inline-grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 1px solid #d8dee7;
  background: #ffffff;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding: 18px 2px;
}

.message {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.message.user {
  grid-template-columns: minmax(0, 1fr) 34px;
}

.message.user .avatar {
  grid-column: 2;
  grid-row: 1;
}

.message.user p {
  grid-column: 1;
  justify-self: end;
  background: #eaf2ff;
}

.avatar {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid #d8dee7;
  border-radius: 50%;
  background: #ffffff;
  color: #1f6feb;
}

.message p {
  max-width: 760px;
  padding: 11px 13px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  border-radius: 6px;
  color: #243044;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.error-message {
  margin-bottom: 10px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #991b1b;
  border-radius: 6px;
  font-size: 13px;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 96px;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid #e5eaf0;
}

textarea {
  width: 100%;
  min-height: 76px;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 11px 12px;
  color: #172033;
  font: inherit;
}

button[type='submit'] {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  align-self: end;
  border: 0;
  background: #1f6feb;
  color: #ffffff;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
}

button[disabled] {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 700px) {
  .chat-panel {
    min-height: 560px;
  }

  .composer {
    grid-template-columns: 1fr;
  }
}
</style>
