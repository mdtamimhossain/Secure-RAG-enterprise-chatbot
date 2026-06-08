<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { FileText, Plus, Search, Send, ShieldCheck } from '@lucide/vue'
import { createConversation, getChatHistory, getConversations, sendChatMessage } from '../services/api'

const props = defineProps({
  role: {
    type: String,
    required: true,
  },
  roleLabel: {
    type: String,
    required: true,
  },
  userName: {
    type: String,
    required: true,
  },
  sessionToken: {
    type: String,
    required: true,
  },
  initialConversationId: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['conversation-change'])

const question = ref('')
const loading = ref(false)
const error = ref('')
const messageList = ref(null)
const messages = ref([])
const conversationId = ref(props.initialConversationId)
const conversations = ref([])

const canSend = computed(() => question.value.trim().length > 0 && !loading.value)
const hasConversation = computed(() => messages.value.length > 0)

onMounted(async () => {
  await loadConversations()
  await loadSavedMessages()
})

watch(
  () => [props.sessionToken, props.initialConversationId],
  async () => {
    conversationId.value = props.initialConversationId
    await loadConversations()
    await loadSavedMessages()
    error.value = ''
  },
)

async function submitQuestion() {
  if (!canSend.value) return

  const currentQuestion = question.value.trim()
  const chatHistory = recentHistory()
  question.value = ''
  error.value = ''
  messages.value.push({ sender: 'user', text: currentQuestion, createdAt: timestamp() })
  scrollToBottom()
  loading.value = true

  try {
    const response = await sendChatMessage({
      question: currentQuestion,
      role: props.role,
      history: chatHistory,
      sessionToken: props.sessionToken,
      conversationId: conversationId.value,
    })

    messages.value.push({
      sender: 'assistant',
      text: response.answer,
      sources: response.sources || [],
      guardrail: response.guardrail || null,
      createdAt: timestamp(),
    })
    await loadConversations()
    scrollToBottom()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function useSuggestion(text) {
  question.value = text
}

async function clearChat() {
  try {
    const conversation = await createConversation({
      sessionToken: props.sessionToken,
      title: 'New chat',
    })
    conversationId.value = conversation.id
    emit('conversation-change', conversation.id)
    await loadConversations()
  } catch (err) {
    error.value = err.message
    return
  }
  messages.value = []
  error.value = ''
}

async function selectConversation(selectedConversationId) {
  if (conversationId.value === selectedConversationId) return

  conversationId.value = selectedConversationId
  emit('conversation-change', selectedConversationId)
  error.value = ''
  await loadSavedMessages()
}

function recentHistory() {
  return messages.value
    .filter((message) => ['user', 'assistant'].includes(message.sender) && message.text?.trim())
    .slice(-8)
    .map((message) => ({
      role: message.sender === 'assistant' ? 'assistant' : 'user',
      content: message.text.trim(),
    }))
}

async function loadSavedMessages() {
  if (!props.sessionToken || !conversationId.value) {
    messages.value = []
    return
  }

  try {
    const history = await getChatHistory({
      sessionToken: props.sessionToken,
      conversationId: conversationId.value,
    })
    messages.value = Array.isArray(history) ? normalizeSavedMessages(history) : []
    scrollToBottom()
  } catch (err) {
    error.value = err.message
    messages.value = []
  }
}

async function loadConversations() {
  if (!props.sessionToken) {
    conversations.value = []
    return
  }

  try {
    const response = await getConversations({ sessionToken: props.sessionToken })
    conversations.value = Array.isArray(response) ? response : []

    if (!conversationId.value && conversations.value.length) {
      conversationId.value = conversations.value[0].id
      emit('conversation-change', conversationId.value)
    }
  } catch (err) {
    error.value = err.message
    conversations.value = []
  }
}

function normalizeSavedMessages(savedMessages) {
  if (
    savedMessages.length === 1 &&
    savedMessages[0]?.sender === 'assistant' &&
    savedMessages[0]?.text?.includes('retrieve authorized context')
  ) {
    return []
  }

  return savedMessages
}

function labelFor(source) {
  const metadata = source.metadata || {}
  return metadata.filename || metadata.source || 'Company document'
}

function conversationLabel(conversation, index) {
  if (conversation.title && conversation.title !== 'New chat') {
    return conversation.title
  }

  return `Chat ${conversations.value.length - index}`
}

function timestamp() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function scrollToBottom() {
  await nextTick()
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}
</script>

<template>
  <section class="assistant-screen" aria-label="AI assistant">
    <div class="conversation-toolbar">
      <button class="clear-chat" type="button" @click="clearChat">
        New chat
      </button>
      <div v-if="conversations.length" class="conversation-tabs" aria-label="Saved conversations">
        <button
          v-for="(conversation, index) in conversations"
          :key="conversation.id"
          class="conversation-tab"
          :class="{ active: conversation.id === conversationId }"
          type="button"
          @click="selectConversation(conversation.id)"
        >
          {{ conversationLabel(conversation, index) }}
        </button>
      </div>
    </div>

    <div ref="messageList" class="conversation" :class="{ empty: !hasConversation }" aria-live="polite">
      <div v-if="!hasConversation" class="assistant-home">
        <h2>What are you working on?</h2>

        <form class="prompt-shell" @submit.prevent="submitQuestion">
          <button class="prompt-icon" type="button" title="Add context">
            <Plus :size="24" aria-hidden="true" />
          </button>
          <textarea
            v-model="question"
            rows="1"
            placeholder="Ask anything"
            @keydown.enter.exact.prevent="submitQuestion"
          />
          <span class="mode-pill">Internal RAG</span>
          <button class="send-button" type="submit" :disabled="!canSend" title="Send question">
            <Send :size="18" aria-hidden="true" />
          </button>
        </form>

        <div class="suggestion-row">
          <button type="button" @click="useSuggestion('What is the leave policy?')">
            <FileText :size="18" aria-hidden="true" />
            <span>Leave policy</span>
          </button>
          <button type="button" @click="useSuggestion('What benefits can employees use?')">
            <ShieldCheck :size="18" aria-hidden="true" />
            <span>Benefits</span>
          </button>
          <button type="button" @click="useSuggestion('Search my accessible finance documents')">
            <Search :size="18" aria-hidden="true" />
            <span>Search documents</span>
          </button>
        </div>
      </div>

      <article
        v-for="(message, index) in messages"
        :key="`${message.createdAt}-${index}`"
        class="message-row"
        :class="[message.sender, { safety: message.guardrail }]"
      >
        <div class="message-content">
          <div class="message-meta">
            <span>{{ message.sender === 'assistant' ? 'Codemars Assistant' : userName }}</span>
            <time>{{ message.createdAt }}</time>
          </div>
          <div v-if="message.guardrail" class="safety-label">
            <ShieldCheck :size="15" aria-hidden="true" />
            <span>Guardrail active - {{ message.guardrail.reason.replaceAll('_', ' ') }}</span>
          </div>
          <p>{{ message.text }}</p>

          <ol v-if="message.sender === 'assistant' && message.sources?.length" class="inline-references">
            <li v-for="(source, sourceIndex) in message.sources" :key="`${labelFor(source)}-${sourceIndex}`">
              <span>{{ sourceIndex + 1 }}</span>
              <div>
                <strong>{{ labelFor(source) }}</strong>
                <small>
                  {{ source.metadata?.department || 'general' }} /
                  {{ source.metadata?.category || 'general' }}
                </small>
              </div>
            </li>
          </ol>
        </div>
      </article>

      <article v-if="loading" class="message-row assistant">
        <div class="message-content">
          <div class="message-meta">
            <span>Codemars Assistant</span>
            <time>Retrieving</time>
          </div>
          <div class="thinking-line">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </article>
    </div>

    <p v-if="error" class="error-message">{{ error }}</p>

    <form v-if="hasConversation" class="prompt-shell sticky" @submit.prevent="submitQuestion">
      <button class="prompt-icon" type="button" title="Add context">
        <Plus :size="22" aria-hidden="true" />
      </button>
      <textarea
        v-model="question"
        rows="1"
        placeholder="Ask a follow-up"
        @keydown.enter.exact.prevent="submitQuestion"
      />
      <span class="mode-pill">{{ roleLabel }}</span>
      <button class="send-button" type="submit" :disabled="!canSend" title="Send question">
        <Send :size="18" aria-hidden="true" />
      </button>
    </form>
  </section>
</template>

<style scoped>
.assistant-screen {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  color: var(--text, #172033);
}

.assistant-screen::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 118px;
  pointer-events: none;
  content: '';
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--app-bg, #0b1020) 0%, transparent),
    var(--app-bg, #0b1020) 54%
  );
  z-index: 3;
}

.conversation-toolbar {
  position: absolute;
  top: 2px;
  left: 0;
  right: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.clear-chat,
.conversation-tab {
  border: 1px solid var(--border, #d8dee7);
  border-radius: 999px;
  background: var(--surface, #ffffff);
  color: var(--muted, #64748b);
  padding: 7px 11px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 760;
}

.conversation-tabs {
  display: flex;
  min-width: 0;
  gap: 7px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: thin;
}

.conversation-tab {
  max-width: 140px;
  flex: 0 0 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-tab.active {
  border-color: color-mix(in srgb, var(--role-accent, #1f6feb) 42%, var(--border));
  background: color-mix(in srgb, var(--role-accent, #1f6feb) 12%, var(--surface));
  color: var(--heading, #111827);
}

.conversation {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 54px 8px 136px;
  scroll-behavior: smooth;
}

.conversation.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
  padding: 0 0 12vh;
}

.assistant-home {
  display: flex;
  width: min(960px, 92%);
  flex-direction: column;
  align-items: center;
  gap: 28px;
  animation: riseIn 220ms ease both;
}

.assistant-home h2 {
  margin: 0;
  color: var(--heading, #111827);
  font-size: clamp(30px, 3.4vw, 38px);
  font-weight: 430;
  letter-spacing: 0;
  text-align: center;
}

.prompt-shell {
  display: flex;
  width: min(960px, 100%);
  align-items: center;
  gap: 10px;
  min-height: 60px;
  border: 1px solid var(--composer-border, #d8dee7);
  border-radius: 999px;
  background: var(--composer-bg, #ffffff);
  padding: 7px 10px 7px 16px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.1);
}

.prompt-shell.sticky {
  position: absolute;
  right: 50%;
  bottom: 18px;
  z-index: 5;
  width: min(860px, 92%);
  margin: 0;
  transform: translateX(50%);
}

.prompt-icon,
.send-button {
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  cursor: pointer;
}

.prompt-icon {
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  background: transparent;
  color: var(--text, #172033);
}

textarea {
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
  min-height: 26px;
  max-height: 130px;
  resize: none;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text, #172033);
  font: inherit;
  font-size: 16px;
  line-height: 1.5;
}

.mode-pill {
  flex: 0 0 auto;
  color: var(--muted, #64748b);
  font-size: 14px;
  white-space: nowrap;
}

.send-button {
  flex: 0 0 38px;
  width: 38px;
  height: 38px;
  background: var(--heading, #111827);
  color: var(--surface, #ffffff);
}

.send-button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.suggestion-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.suggestion-row button {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 48px;
  border: 1px solid var(--border, #d8dee7);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface) 72%, transparent);
  color: var(--text, #172033);
  padding: 0 18px;
  cursor: pointer;
  font-weight: 720;
}

.message-row {
  width: min(850px, 100%);
  margin: 0 auto 20px;
  animation: riseIn 180ms ease both;
}

.message-row.user {
  display: flex;
  justify-content: flex-end;
}

.message-content {
  width: 100%;
  border-bottom: 1px solid var(--border, #d8dee7);
  padding: 0 0 18px;
}

.message-row.user .message-content {
  width: fit-content;
  max-width: min(680px, 72%);
  border: 1px solid var(--border, #d8dee7);
  border-radius: 22px;
  background: var(--surface-soft, #f8fbff);
  padding: 14px 16px;
}

.message-row.safety .message-content {
  border: 1px solid color-mix(in srgb, #f59e0b 38%, var(--border));
  border-radius: 16px;
  background: color-mix(in srgb, #f59e0b 9%, var(--surface));
  padding: 14px 16px;
}

.safety-label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: #b45309;
  font-size: 12px;
  font-weight: 820;
  text-transform: capitalize;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 8px;
  color: var(--muted, #64748b);
  font-size: 12px;
  font-weight: 780;
}

.message-content p {
  margin: 0;
  color: var(--text, #172033);
  font-size: 15px;
  line-height: 1.75;
  white-space: pre-wrap;
}

.inline-references {
  display: grid;
  gap: 8px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.inline-references li {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 9px;
  align-items: start;
  border: 1px solid var(--border, #d8dee7);
  border-radius: 12px;
  background: color-mix(in srgb, var(--surface-soft) 72%, transparent);
  padding: 10px;
}

.inline-references li > span {
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 50%;
  background: var(--heading, #111827);
  color: var(--surface, #ffffff);
  font-size: 12px;
  font-weight: 850;
}

.inline-references strong,
.inline-references small {
  display: block;
}

.inline-references strong {
  overflow: hidden;
  color: var(--heading, #111827);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inline-references small {
  margin-top: 2px;
  color: var(--muted, #64748b);
  font-size: 12px;
  text-transform: capitalize;
}

.thinking-line {
  display: flex;
  gap: 6px;
  min-height: 24px;
  align-items: center;
}

.thinking-line span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted, #64748b);
  animation: typingPulse 900ms infinite ease-in-out;
}

.thinking-line span:nth-child(2) {
  animation-delay: 120ms;
}

.thinking-line span:nth-child(3) {
  animation-delay: 240ms;
}

.error-message {
  justify-self: center;
  width: min(850px, 100%);
  margin: 0 0 10px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fff1f2;
  color: #991b1b;
  padding: 10px 12px;
  font-size: 13px;
}

@keyframes riseIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes typingPulse {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-4px);
  }
}

@media (max-width: 760px) {
  .assistant-screen {
    height: 100%;
    min-height: 0;
  }

  .prompt-shell {
    min-height: 56px;
    border-radius: 24px;
    padding-left: 12px;
  }

  .mode-pill {
    display: none;
  }
}
</style>
