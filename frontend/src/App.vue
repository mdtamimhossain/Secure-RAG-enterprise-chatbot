<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  BadgeCheck,
  Bot,
  Building2,
  ClipboardList,
  Database,
  FileLock2,
  LayoutDashboard,
  LogOut,
  Moon,
  MessageCircle,
  Shield,
  Sparkles,
  Sun,
  UsersRound,
} from '@lucide/vue'
import ChatBox from './components/ChatBox.vue'
import RoleSelector from './components/RoleSelector.vue'
import { getMonitoringMetrics, getServiceStatus } from './services/api'

const sessionStarted = ref(false)
const loginName = ref('')
const loginRole = ref('employee')
const selectedRole = ref('employee')
const activeView = ref('workspace')
const status = ref(null)
const statusError = ref('')
const metrics = ref(null)
const metricsError = ref('')
const isDarkMode = ref(true)

const roleProfiles = {
  employee: {
    label: 'Employee',
    title: 'Product Associate',
    department: 'Employee Workspace',
    location: 'Berlin',
    manager: 'Maya Chen',
    access: 'General employee documents',
    focus: 'benefits, leave, company handbook, workplace tools',
    accent: '#1f6feb',
  },
  hr: {
    label: 'HR',
    title: 'People Operations Partner',
    department: 'Human Resources',
    location: 'London',
    manager: 'Priya Nair',
    access: 'General documents and HR policies',
    focus: 'leave policy, benefits, onboarding, employee handbook',
    accent: '#b4237a',
  },
  finance: {
    label: 'Finance',
    title: 'Finance Analyst',
    department: 'Finance',
    location: 'New York',
    manager: 'Omar Rahman',
    access: 'General documents and finance reports',
    focus: 'annual reports, budget context, revenue documents',
    accent: '#047857',
  },
  executive: {
    label: 'Executive',
    title: 'Executive Leader',
    department: 'Leadership Office',
    location: 'New York',
    manager: 'Board Office',
    access: 'All indexed company departments',
    focus: 'cross-department policy and strategic document review',
    accent: '#7c3aed',
  },
}

const navItems = [
  { id: 'workspace', label: 'Workspace', icon: LayoutDashboard },
  { id: 'assistant', label: 'Assistant', icon: Bot },
  { id: 'documents', label: 'Documents', icon: FileLock2 },
  { id: 'directory', label: 'Directory', icon: UsersRound },
]

const documentsByRole = {
  employee: [
    { name: 'Employee Handbook', department: 'General', category: 'Handbook', access: 'Available' },
    { name: 'Benefits and Perks', department: 'General', category: 'Benefits', access: 'Available' },
    { name: 'IT Security Basics', department: 'General', category: 'Security', access: 'Available' },
    { name: 'Remote Work Guidelines', department: 'General', category: 'Remote Work', access: 'Available' },
    { name: 'Helpdesk Support Guide', department: 'General', category: 'Support', access: 'Available' },
  ],
  hr: [
    { name: 'Employee Handbook', department: 'General', category: 'Handbook', access: 'Available' },
    { name: 'Benefits and Perks', department: 'General', category: 'Benefits', access: 'Available' },
    { name: 'Leave Policy', department: 'HR', category: 'Leave', access: 'Available' },
    { name: 'Onboarding Playbook', department: 'HR', category: 'People Ops', access: 'Available' },
    { name: 'Employee Relations Process', department: 'HR', category: 'Employee Relations', access: 'Available' },
  ],
  finance: [
    { name: 'Employee Handbook', department: 'General', category: 'Handbook', access: 'Available' },
    { name: 'Q2 Budget Plan', department: 'Finance', category: 'Finance Report', access: 'Available' },
    { name: 'Procurement Policy', department: 'Finance', category: 'Procurement', access: 'Available' },
    { name: 'Expense Reimbursement Policy', department: 'Finance', category: 'Expense', access: 'Available' },
    { name: 'Revenue Recognition Notes', department: 'Finance', category: 'Revenue', access: 'Available' },
  ],
  executive: [
    { name: 'Employee Handbook', department: 'General', category: 'Handbook', access: 'Available' },
    { name: 'Leave Policy', department: 'HR', category: 'Leave', access: 'Available' },
    { name: 'Q2 Budget Plan', department: 'Finance', category: 'Finance Report', access: 'Available' },
    { name: 'Revenue Recognition Notes', department: 'Finance', category: 'Revenue', access: 'Available' },
    { name: 'Executive Strategy Memo', department: 'Executive', category: 'Strategy', access: 'Available' },
    { name: 'Board Metrics', department: 'Executive', category: 'Board', access: 'Available' },
    { name: 'Acquisition Risk Brief', department: 'Executive', category: 'Risk', access: 'Available' },
  ],
}

const directoryByRole = {
  employee: [
    { name: 'Maya Chen', team: 'Engineering', relation: 'Manager', status: 'Available' },
    { name: 'Priya Nair', team: 'Human Resources', relation: 'HR contact', status: 'Busy' },
    { name: 'IT Service Desk', team: 'Operations', relation: 'Support', status: 'Available' },
  ],
  hr: [
    { name: 'Maya Chen', team: 'Engineering', relation: 'Manager', status: 'Available' },
    { name: 'Omar Rahman', team: 'Finance', relation: 'Finance partner', status: 'Away' },
    { name: 'David Lee', team: 'Leadership', relation: 'Executive sponsor', status: 'Available' },
  ],
  finance: [
    { name: 'Omar Rahman', team: 'Finance', relation: 'Manager', status: 'Available' },
    { name: 'Priya Nair', team: 'Human Resources', relation: 'Policy contact', status: 'Busy' },
    { name: 'David Lee', team: 'Leadership', relation: 'Reviewer', status: 'Available' },
  ],
  executive: [
    { name: 'Maya Chen', team: 'Engineering', relation: 'Engineering lead', status: 'Available' },
    { name: 'Priya Nair', team: 'Human Resources', relation: 'People lead', status: 'Busy' },
    { name: 'Omar Rahman', team: 'Finance', relation: 'Finance lead', status: 'Available' },
  ],
}

const activeProfile = computed(() => roleProfiles[selectedRole.value] || roleProfiles.employee)
const loginProfile = computed(() => roleProfiles[loginRole.value] || roleProfiles.employee)
const displayName = computed(() => loginName.value.trim() || 'Demo User')
const availableDocuments = computed(() => documentsByRole[selectedRole.value] || documentsByRole.employee)
const directoryPeople = computed(() => directoryByRole[selectedRole.value] || directoryByRole.employee)
const topSourceDepartments = computed(() => {
  const departments = metrics.value?.source_departments || {}
  return Object.entries(departments)
    .sort((first, second) => second[1] - first[1])
    .slice(0, 3)
})

const initials = computed(() =>
  displayName.value
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
)

function startSession() {
  if (!loginName.value.trim()) return
  selectedRole.value = loginRole.value
  activeView.value = 'workspace'
  sessionStarted.value = true
}

function signOut() {
  sessionStarted.value = false
}

function switchView(viewId) {
  activeView.value = viewId
}

function toggleTheme() {
  isDarkMode.value = !isDarkMode.value
}

onMounted(async () => {
  try {
    const [serviceStatus, monitoringMetrics] = await Promise.all([
      getServiceStatus(),
      getMonitoringMetrics(),
    ])
    status.value = serviceStatus
    metrics.value = monitoringMetrics
  } catch (error) {
    statusError.value = error.message
    metricsError.value = error.message
  }
})
</script>

<template>
  <main v-if="!sessionStarted" class="login-screen">
    <div class="animated-field" aria-hidden="true">
      <span class="pulse pulse-one"></span>
      <span class="pulse pulse-two"></span>
      <span class="pulse pulse-three"></span>
    </div>

    <section class="login-panel" aria-label="Demo login">
      <div class="login-copy">
        <div class="portal-badge">
          <Sparkles :size="18" aria-hidden="true" />
          <span>Codemars Intranet Preview</span>
        </div>
        <h1>Enter the employee AI workspace</h1>
        <p>
          Choose a demo role, add a name, and the portal will adapt access, profile details,
          assistant context, and document retrieval to that session.
        </p>
      </div>

      <form class="login-card" @submit.prevent="startSession">
        <label>
          <span>Your display name</span>
          <input v-model="loginName" type="text" placeholder="e.g. Sara Khan" autocomplete="name" />
        </label>

        <div class="login-role-block">
          <span>Choose demo role</span>
          <RoleSelector v-model="loginRole" />
        </div>

        <div class="login-preview" :style="{ borderColor: loginProfile.accent }">
          <div class="preview-avatar" :style="{ background: loginProfile.accent }">
            {{ loginName.trim() ? initials : 'AI' }}
          </div>
          <div>
            <strong>{{ loginName.trim() || 'Your session' }}</strong>
            <span>{{ loginProfile.title }} - {{ loginProfile.department }}</span>
          </div>
        </div>

        <button class="login-button" type="submit" :disabled="!loginName.trim()">
          <Shield :size="18" aria-hidden="true" />
          <span>Enter Workspace</span>
        </button>
      </form>
    </section>
  </main>

  <div
    v-else
    class="app-shell"
    :class="{ 'dark-mode': isDarkMode }"
    :style="{ '--role-accent': activeProfile.accent }"
  >
    <aside class="sidebar" aria-label="Primary navigation">
      <div class="sidebar-top">
        <div class="brand">
          <div class="brand-mark">
            <Building2 :size="22" aria-hidden="true" />
          </div>
          <div>
            <strong>Codemars Intranet</strong>
            <span>{{ activeProfile.label }} access</span>
          </div>
        </div>

        <nav>
          <button
            v-for="item in navItems"
            :key="item.id"
            type="button"
            :class="{ active: activeView === item.id }"
            @click="switchView(item.id)"
          >
            <component :is="item.icon" :size="18" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
        </nav>
      </div>

      <div class="sidebar-footer">
        <div class="security-note">
          <Shield :size="18" aria-hidden="true" />
          <span>RBAC filtering active</span>
        </div>

        <button class="user-menu" type="button" title="Change user" @click="signOut">
          <div class="avatar-chip">{{ initials }}</div>
          <div>
            <span>{{ displayName }}</span>
            <small>{{ activeProfile.title }}</small>
          </div>
          <LogOut :size="16" aria-hidden="true" />
        </button>
      </div>
    </aside>

    <main class="main-area" :class="{ 'assistant-main': activeView === 'assistant' }">
      <header class="topbar" :class="{ 'assistant-topbar': activeView === 'assistant' }">
        <div v-if="activeView !== 'assistant'">
          <h1>{{ activeProfile.label }} AI Knowledge Assistant</h1>
          <span class="topbar-subtitle">
            Role-aware search across company documents, policies, and internal knowledge.
          </span>
        </div>
        <button class="theme-icon-button" type="button" :title="isDarkMode ? 'Light mode' : 'Dark mode'" @click="toggleTheme">
          <Sun v-if="isDarkMode" :size="18" aria-hidden="true" />
          <Moon v-else :size="18" aria-hidden="true" />
        </button>
      </header>

      <section v-if="activeView === 'workspace'" class="dashboard-hero view-enter">
        <span>Access locked to {{ activeProfile.label }}</span>
        <h2>Chat with AI Assistant</h2>
        <p>Ask questions from the documents your current role is allowed to read.</p>
        <button type="button" @click="switchView('assistant')">
          <MessageCircle :size="18" aria-hidden="true" />
          <span>Open Assistant</span>
        </button>
      </section>

      <section v-if="activeView === 'workspace'" class="summary-grid view-enter" aria-label="Workspace summary">
        <div class="summary-item">
          <BadgeCheck :size="20" aria-hidden="true" />
          <div>
            <span>Signed in as</span>
            <strong>{{ activeProfile.title }}</strong>
          </div>
        </div>
        <div class="summary-item">
          <Shield :size="20" aria-hidden="true" />
          <div>
            <span>Current access</span>
            <strong>{{ activeProfile.access }}</strong>
          </div>
        </div>
        <div class="summary-item">
          <Database :size="20" aria-hidden="true" />
          <div>
            <span>Indexed chunks</span>
            <strong>{{ status?.chunk_count ?? 'Loading' }}</strong>
          </div>
        </div>
        <div class="summary-item">
          <ClipboardList :size="20" aria-hidden="true" />
          <div>
            <span>Session focus</span>
            <strong>{{ activeProfile.focus }}</strong>
          </div>
        </div>
      </section>

      <p v-if="statusError" class="status-error">{{ statusError }}</p>
      <p v-else-if="metricsError" class="status-error">{{ metricsError }}</p>

      <section v-if="activeView === 'workspace'" class="monitoring-panel view-enter" aria-label="Assistant monitoring">
        <div class="monitoring-header">
          <div>
            <span>Live monitoring</span>
            <h2>Assistant activity</h2>
          </div>
          <Database :size="22" aria-hidden="true" />
        </div>

        <div class="metric-grid">
          <div class="metric-card">
            <span>Total chats</span>
            <strong>{{ metrics?.total_chats ?? 0 }}</strong>
          </div>
          <div class="metric-card">
            <span>Blocked</span>
            <strong>{{ metrics?.blocked_chats ?? 0 }}</strong>
          </div>
          <div class="metric-card">
            <span>Avg latency</span>
            <strong>{{ metrics?.average_latency_ms ?? 0 }} ms</strong>
          </div>
          <div class="metric-card">
            <span>Avg sources</span>
            <strong>{{ metrics?.average_source_count ?? 0 }}</strong>
          </div>
        </div>

        <div class="monitoring-details">
          <div>
            <span>Top source departments</span>
            <p v-if="!topSourceDepartments.length">No document-backed answers yet.</p>
            <ul v-else>
              <li v-for="[department, count] in topSourceDepartments" :key="department">
                <strong>{{ department }}</strong>
                <small>{{ count }} hits</small>
              </li>
            </ul>
          </div>
          <div>
            <span>Guardrail blocks</span>
            <p v-if="!Object.keys(metrics?.guardrail_reasons || {}).length">No blocked prompts yet.</p>
            <ul v-else>
              <li v-for="(count, reason) in metrics.guardrail_reasons" :key="reason">
                <strong>{{ reason.replaceAll('_', ' ') }}</strong>
                <small>{{ count }} blocked</small>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section v-if="activeView === 'assistant'" class="assistant-page view-enter">
        <div class="workspace-panel chat-wrap">
          <ChatBox
            :role="selectedRole"
            :role-label="activeProfile.label"
            :user-name="displayName"
          />
        </div>
      </section>

      <section v-if="activeView === 'documents'" class="view-page view-enter">
        <div class="view-header">
          <div>
            <h2>Document Access</h2>
            <p>{{ activeProfile.label }} role can search {{ activeProfile.access.toLowerCase() }}.</p>
          </div>
          <FileLock2 :size="24" aria-hidden="true" />
        </div>

        <div class="data-table">
          <div class="table-row table-head">
            <span>Document</span>
            <span>Department</span>
            <span>Category</span>
            <span>Status</span>
          </div>
          <div v-for="document in availableDocuments" :key="document.name" class="table-row">
            <strong>{{ document.name }}</strong>
            <span>{{ document.department }}</span>
            <span>{{ document.category }}</span>
            <em>{{ document.access }}</em>
          </div>
        </div>
      </section>

      <section v-if="activeView === 'directory'" class="view-page view-enter">
        <div class="view-header">
          <div>
            <h2>Internal Directory</h2>
            <p>Demo contacts matched to {{ displayName }}'s {{ activeProfile.label }} session.</p>
          </div>
          <UsersRound :size="24" aria-hidden="true" />
        </div>

        <div class="directory-grid">
          <article v-for="person in directoryPeople" :key="person.name" class="person-card">
            <div class="person-avatar">{{ person.name.split(' ').map((part) => part[0]).join('') }}</div>
            <div>
              <h3>{{ person.name }}</h3>
              <p>{{ person.relation }}</p>
              <span>{{ person.team }}</span>
            </div>
            <em :class="person.status.toLowerCase()">{{ person.status }}</em>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
* {
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100%;
  margin: 0;
}

body {
  background: #f4f7fb;
  color: #172033;
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    sans-serif;
}

button,
textarea,
select,
input {
  font: inherit;
}

.login-screen {
  position: relative;
  display: grid;
  min-height: 100vh;
  place-items: center;
  overflow: hidden;
  padding: 28px;
  background:
    radial-gradient(circle at 20% 20%, rgba(31, 111, 235, 0.34), transparent 30%),
    radial-gradient(circle at 78% 16%, rgba(180, 35, 122, 0.24), transparent 28%),
    radial-gradient(circle at 66% 82%, rgba(4, 120, 87, 0.25), transparent 30%),
    #0f172a;
}

.animated-field {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.pulse {
  position: absolute;
  width: 220px;
  height: 220px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 24px;
  animation: drift 12s ease-in-out infinite;
}

.pulse-one {
  top: 12%;
  left: 10%;
  background: rgba(96, 165, 250, 0.16);
}

.pulse-two {
  right: 8%;
  bottom: 14%;
  background: rgba(52, 211, 153, 0.14);
  animation-delay: -4s;
}

.pulse-three {
  right: 20%;
  top: 10%;
  width: 150px;
  height: 150px;
  background: rgba(244, 114, 182, 0.15);
  animation-delay: -8s;
}

@keyframes drift {
  0%,
  100% {
    transform: translate3d(0, 0, 0) rotate(0deg);
  }
  50% {
    transform: translate3d(18px, -24px, 0) rotate(9deg);
  }
}

.login-panel {
  position: relative;
  display: grid;
  width: min(1040px, 100%);
  grid-template-columns: minmax(0, 0.95fr) minmax(380px, 0.75fr);
  gap: 28px;
  align-items: center;
}

.login-copy {
  color: #ffffff;
}

.portal-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  color: #dbeafe;
  font-size: 13px;
  font-weight: 750;
}

.login-copy h1 {
  max-width: 680px;
  margin: 18px 0 12px;
  color: #ffffff;
  font-size: 52px;
  line-height: 1.03;
}

.login-copy p {
  max-width: 610px;
  margin: 0;
  color: #dbeafe;
  font-size: 17px;
  line-height: 1.55;
}

.login-card {
  display: grid;
  gap: 18px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.93);
  padding: 22px;
  box-shadow: 0 26px 60px rgba(2, 6, 23, 0.25);
  backdrop-filter: blur(12px);
}

label span,
.login-role-block > span {
  display: block;
  margin-bottom: 8px;
  color: #334155;
  font-size: 13px;
  font-weight: 760;
}

input {
  width: 100%;
  min-height: 46px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 12px;
  color: #111827;
  background: #ffffff;
}

.login-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 2px solid;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.preview-avatar,
.avatar-chip {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  font-weight: 800;
}

.login-preview strong,
.login-preview span {
  display: block;
}

.login-preview span {
  margin-top: 2px;
  color: #64748b;
  font-size: 13px;
}

.login-button,
.signout-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 800;
}

.login-button {
  min-height: 48px;
  background: linear-gradient(135deg, #1f6feb, #7c3aed);
  color: #ffffff;
}

.login-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.app-shell {
  --role-accent: #1f6feb;
  --app-bg: #eef2f7;
  --surface: #ffffff;
  --surface-soft: #f8fbff;
  --border: #dbe3ee;
  --text: #172033;
  --heading: #111827;
  --muted: #64748b;
  --muted-strong: #1e3a8a;
  --soft-shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
  --composer-bg: #ffffff;
  --composer-border: #d8dee7;
  display: grid;
  min-height: 100vh;
  grid-template-columns: 268px minmax(0, 1fr);
  background: var(--app-bg);
  color: var(--text);
  transition:
    background 180ms ease,
    color 180ms ease;
}

.app-shell.dark-mode {
  --app-bg: #0b1020;
  --surface: #111827;
  --surface-soft: #172033;
  --border: #273449;
  --text: #e5edf7;
  --heading: #f8fafc;
  --muted: #9aa7ba;
  --muted-strong: #bfdbfe;
  --soft-shadow: 0 18px 48px rgba(0, 0, 0, 0.24);
  --composer-bg: #242424;
  --composer-border: #343434;
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
  height: 100vh;
  border-right: 1px solid var(--border);
  background: linear-gradient(180deg, var(--surface) 0%, var(--surface-soft) 100%);
  padding: 22px 16px;
}

.sidebar-top,
.sidebar-footer {
  display: grid;
  gap: 22px;
}

.sidebar-footer {
  gap: 12px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 52px;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 6px;
  background: var(--role-accent);
  color: #ffffff;
}

.brand strong,
.brand span,
.user-menu span,
.user-menu small,
.summary-item span,
.summary-item strong {
  display: block;
}

.brand strong {
  color: var(--heading);
  font-size: 14px;
  letter-spacing: 0;
}

.brand span {
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
}

.user-menu {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  padding: 11px;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.user-menu:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--role-accent) 32%, var(--border));
  box-shadow: var(--soft-shadow);
}

.user-menu span {
  overflow: hidden;
  color: var(--heading);
  font-weight: 760;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-menu small {
  overflow: hidden;
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-menu svg {
  color: var(--muted);
}

nav {
  display: grid;
  gap: 6px;
}

nav button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 40px;
  border: 0;
  border-radius: 6px;
  padding: 0 10px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-weight: 650;
  font-size: 14px;
  text-align: left;
  transition:
    transform 150ms ease,
    background 150ms ease,
    color 150ms ease;
}

nav button:hover {
  transform: translateX(2px);
  background: color-mix(in srgb, var(--role-accent) 9%, var(--surface));
}

nav button.active {
  background: color-mix(in srgb, var(--role-accent) 15%, var(--surface));
  color: var(--role-accent);
}

.theme-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--muted);
  cursor: pointer;
  font-weight: 800;
}

.theme-button:hover {
  border-color: color-mix(in srgb, var(--role-accent) 32%, var(--border));
  color: var(--heading);
}

.theme-icon-button {
  display: inline-grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--heading);
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease;
}

.theme-icon-button:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--role-accent) 36%, var(--border));
  background: color-mix(in srgb, var(--role-accent) 9%, var(--surface));
}

.security-note {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-soft);
  padding: 12px;
  color: var(--muted-strong);
  font-size: 13px;
  font-weight: 700;
}

.main-area {
  min-width: 0;
  padding: 24px;
}

.main-area.assistant-main {
  height: 100vh;
  min-height: 0;
  overflow: hidden;
  padding: 22px 28px 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  padding: 14px 16px;
  box-shadow: var(--soft-shadow);
  backdrop-filter: blur(16px);
}

.topbar.assistant-topbar {
  justify-content: flex-end;
  border: 0;
  background: transparent;
  margin-bottom: 0;
  padding: 0;
  box-shadow: none;
  backdrop-filter: none;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: var(--heading);
  font-size: 28px;
  font-weight: 760;
}

.topbar-subtitle {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 14px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-chip {
  width: 38px;
  height: 38px;
  background: var(--role-accent);
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.dashboard-hero {
  display: grid;
  gap: 12px;
  justify-items: start;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--role-accent) 11%, var(--surface)), var(--surface) 58%),
    var(--surface);
  margin-bottom: 16px;
  padding: 22px;
  box-shadow: var(--soft-shadow);
}

.dashboard-hero > span {
  border: 1px solid color-mix(in srgb, var(--role-accent) 30%, var(--border));
  border-radius: 999px;
  background: color-mix(in srgb, var(--role-accent) 10%, var(--surface));
  color: var(--role-accent);
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 820;
}

.dashboard-hero h2 {
  margin: 0;
  color: var(--heading);
  font-size: 28px;
  line-height: 1.15;
}

.dashboard-hero p {
  max-width: 640px;
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.55;
}

.dashboard-hero button {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 42px;
  border: 0;
  border-radius: 999px;
  background: var(--heading);
  color: var(--surface);
  padding: 0 16px;
  cursor: pointer;
  font-weight: 820;
}

.workspace-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.55fr);
  gap: 16px;
  margin-bottom: 16px;
}

.overview-hero,
.session-card {
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--role-accent) 12%, var(--surface)), var(--surface) 54%),
    var(--surface);
  box-shadow: var(--soft-shadow);
}

.overview-hero {
  padding: 24px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--role-accent) 30%, var(--border));
  border-radius: 999px;
  background: color-mix(in srgb, var(--role-accent) 10%, var(--surface));
  padding: 7px 10px;
  color: var(--role-accent);
  font-size: 12px;
  font-weight: 820;
}

.overview-hero h2 {
  margin: 16px 0 8px;
  color: var(--heading);
  font-size: 30px;
  line-height: 1.15;
}

.overview-hero p {
  max-width: 740px;
  margin: 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.6;
}

.session-card {
  display: grid;
  align-content: center;
  gap: 8px;
  padding: 20px;
}

.session-card span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.session-card strong {
  color: var(--heading);
  font-size: 22px;
  line-height: 1.2;
}

.session-card p {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  padding: 14px;
  animation: summaryCardIn 280ms ease both;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.summary-item:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--role-accent) 35%, var(--border));
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.summary-item:nth-child(1) {
  animation-delay: 40ms;
}

.summary-item:nth-child(2) {
  animation-delay: 90ms;
}

.summary-item:nth-child(3) {
  animation-delay: 140ms;
}

.summary-item:nth-child(4) {
  animation-delay: 190ms;
}

.summary-item svg {
  color: var(--role-accent);
  flex: 0 0 auto;
}

.summary-item span {
  color: var(--muted);
  font-size: 12px;
}

.summary-item strong {
  margin-top: 3px;
  color: var(--text);
  font-size: 14px;
}

.monitoring-panel {
  display: grid;
  gap: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  margin-bottom: 16px;
  padding: 16px;
  box-shadow: var(--soft-shadow);
}

.monitoring-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.monitoring-header span,
.monitoring-details span,
.metric-card span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
  text-transform: uppercase;
}

.monitoring-header h2 {
  margin: 3px 0 0;
  color: var(--heading);
  font-size: 18px;
}

.monitoring-header svg {
  color: var(--role-accent);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  display: grid;
  gap: 8px;
  min-height: 86px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--surface-soft) 78%, transparent);
  padding: 13px;
}

.metric-card strong {
  color: var(--heading);
  font-size: 24px;
}

.monitoring-details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.monitoring-details > div {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--surface-soft) 60%, transparent);
  padding: 13px;
}

.monitoring-details p {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.monitoring-details ul {
  display: grid;
  gap: 8px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}

.monitoring-details li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--text);
  font-size: 13px;
  text-transform: capitalize;
}

.monitoring-details small {
  color: var(--muted);
}

.role-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.04);
}

.locked-role-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 64px;
  border: 1px solid color-mix(in srgb, var(--role-accent) 34%, var(--border));
  border-radius: 8px;
  background: color-mix(in srgb, var(--role-accent) 10%, var(--surface));
  padding: 12px;
}

.locked-role-card svg {
  color: var(--role-accent);
}

.locked-role-card strong,
.locked-role-card span {
  display: block;
}

.locked-role-card strong {
  color: var(--text);
}

.locked-role-card span {
  margin-top: 2px;
  color: var(--muted);
  font-size: 13px;
}

.role-section h2,
.role-section p {
  margin: 0;
}

.role-section h2 {
  font-size: 16px;
}

.role-section p {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}

.status-error {
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #991b1b;
  border-radius: 6px;
  padding: 10px 12px;
}

.assistant-page {
  display: flex;
  height: calc(100vh - 64px);
  min-height: 0;
  overflow: hidden;
}

.workspace-panel {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  padding: 16px;
  box-shadow: var(--soft-shadow);
}

.assistant-page .workspace-panel {
  display: flex;
  height: 100%;
  min-height: 0;
  flex: 1;
  border: 0;
  background: transparent;
  padding: 0;
  box-shadow: none;
}

.assistant-page .chat-wrap {
  min-width: 0;
}

.sources-wrap {
  position: sticky;
  top: 20px;
}

.view-enter {
  animation: viewIn 220ms ease both;
}

@keyframes viewIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes summaryCardIn {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.view-page {
  border: 1px solid var(--border);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--role-accent) 9%, var(--surface)), var(--surface) 42%),
    var(--surface);
  padding: 18px;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
  color: var(--role-accent);
}

.view-header h2,
.view-header p {
  margin: 0;
}

.view-header h2 {
  color: var(--text);
  font-size: 20px;
}

.view-header p {
  margin-top: 4px;
  color: var(--muted);
  font-size: 14px;
}

.data-table {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.table-row {
  display: grid;
  grid-template-columns: minmax(190px, 1.2fr) minmax(120px, 0.8fr) minmax(120px, 0.8fr) 96px;
  gap: 12px;
  align-items: center;
  min-height: 54px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  padding: 10px 12px;
}

.table-head {
  min-height: 42px;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.table-row strong {
  color: var(--text);
}

.table-row span {
  color: var(--muted);
}

.table-row em,
.person-card em {
  justify-self: start;
  border-radius: 999px;
  background: color-mix(in srgb, var(--role-accent) 12%, var(--surface));
  color: var(--role-accent);
  padding: 5px 9px;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.directory-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.person-card {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  min-height: 150px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  padding: 14px;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease;
}

.person-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.person-avatar {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 50%;
  background: var(--role-accent);
  color: #ffffff;
  font-weight: 850;
}

.person-card h3,
.person-card p {
  margin: 0;
}

.person-card h3 {
  color: var(--text);
  font-size: 16px;
}

.person-card p {
  margin-top: 4px;
  color: var(--muted);
  font-size: 14px;
}

.person-card span {
  display: block;
  margin-top: 8px;
  color: var(--muted);
  font-size: 13px;
}

.person-card em {
  grid-column: 1 / -1;
  margin-top: 8px;
}

.person-card em.busy {
  background: #fff7ed;
  color: #c2410c;
}

.person-card em.away {
  background: #fefce8;
  color: #a16207;
}

@media (max-width: 1120px) {
  .app-shell {
    grid-template-columns: 82px minmax(0, 1fr);
  }

  .brand div:last-child,
  .user-menu div:nth-child(2),
  .user-menu > svg,
  nav span,
  .security-note span {
    display: none;
  }

  nav button,
  .security-note,
  .user-menu {
    justify-content: center;
  }

  .user-menu {
    grid-template-columns: 38px;
    justify-content: center;
    padding: 8px;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-grid,
  .monitoring-details {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .assistant-page,
  .role-section,
  .login-panel,
  .directory-grid {
    grid-template-columns: 1fr;
  }

  .table-row {
    grid-template-columns: 1fr 1fr;
  }

  .sources-wrap {
    position: static;
  }

  .login-copy h1 {
    font-size: 40px;
  }
}

@media (max-width: 700px) {
  .login-screen {
    padding: 16px;
  }

  .login-copy h1 {
    font-size: 34px;
  }

  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .main-area {
    padding: 16px;
  }

  .topbar {
    align-items: flex-start;
  }

  .topbar-actions {
    justify-content: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .metric-grid,
  .monitoring-details {
    grid-template-columns: 1fr;
  }
}
</style>
