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
  Shield,
  Sparkles,
  UsersRound,
} from '@lucide/vue'
import ChatBox from './components/ChatBox.vue'
import RoleSelector from './components/RoleSelector.vue'
import SourceList from './components/SourceList.vue'
import { getServiceStatus } from './services/api'

const sessionStarted = ref(false)
const loginName = ref('')
const loginRole = ref('employee')
const selectedRole = ref('employee')
const sources = ref([])
const status = ref(null)
const statusError = ref('')

const roleProfiles = {
  employee: {
    label: 'Employee',
    title: 'Product Associate',
    department: 'Employee Workspace',
    location: 'Berlin',
    manager: 'Maya Chen',
    access: 'General documents and HR policies',
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

const activeProfile = computed(() => roleProfiles[selectedRole.value] || roleProfiles.employee)
const loginProfile = computed(() => roleProfiles[loginRole.value] || roleProfiles.employee)
const displayName = computed(() => loginName.value.trim() || 'Demo User')

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
  sessionStarted.value = true
  sources.value = []
}

function signOut() {
  sessionStarted.value = false
  sources.value = []
}

function updateSources(nextSources) {
  sources.value = nextSources
}

onMounted(async () => {
  try {
    status.value = await getServiceStatus()
  } catch (error) {
    statusError.value = error.message
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
          <span>Acme Internal Preview</span>
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
            <span>{{ loginProfile.title }} · {{ loginProfile.department }}</span>
          </div>
        </div>

        <button class="login-button" type="submit" :disabled="!loginName.trim()">
          <Shield :size="18" aria-hidden="true" />
          <span>Enter Workspace</span>
        </button>
      </form>
    </section>
  </main>

  <div v-else class="app-shell" :style="{ '--role-accent': activeProfile.accent }">
    <aside class="sidebar" aria-label="Primary navigation">
      <div class="brand">
        <div class="brand-mark">
          <Building2 :size="22" aria-hidden="true" />
        </div>
        <div>
          <strong>Acme Intranet</strong>
          <span>{{ activeProfile.label }} session</span>
        </div>
      </div>

      <nav>
        <a class="active" href="#">
          <LayoutDashboard :size="18" aria-hidden="true" />
          <span>Workspace</span>
        </a>
        <a href="#">
          <Bot :size="18" aria-hidden="true" />
          <span>Assistant</span>
        </a>
        <a href="#">
          <FileLock2 :size="18" aria-hidden="true" />
          <span>Documents</span>
        </a>
        <a href="#">
          <UsersRound :size="18" aria-hidden="true" />
          <span>Directory</span>
        </a>
      </nav>

      <button class="signout-button" type="button" @click="signOut">
        <LogOut :size="17" aria-hidden="true" />
        <span>Change user</span>
      </button>

      <div class="security-note">
        <Shield :size="18" aria-hidden="true" />
        <span>RBAC filtering active</span>
      </div>
    </aside>

    <main class="main-area">
      <header class="topbar">
        <div>
          <p class="eyebrow">Internal employee workspace</p>
          <h1>{{ activeProfile.label }} AI Knowledge Assistant</h1>
        </div>
        <div class="profile-chip">
          <div class="avatar-chip">{{ initials }}</div>
          <div>
            <span>{{ displayName }}</span>
            <small>{{ activeProfile.department }}</small>
          </div>
        </div>
      </header>

      <section class="summary-grid" aria-label="Workspace summary">
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

      <section class="role-section">
        <div>
          <h2>Access Context</h2>
          <p>{{ displayName }} is currently using {{ activeProfile.label }} document access.</p>
        </div>
        <RoleSelector v-model="selectedRole" />
      </section>

      <p v-if="statusError" class="status-error">{{ statusError }}</p>

      <section class="workspace-grid">
        <div class="workspace-panel chat-wrap">
          <ChatBox
            :role="selectedRole"
            :role-label="activeProfile.label"
            :user-name="displayName"
            @sources-updated="updateSources"
          />
        </div>
        <div class="workspace-panel sources-wrap">
          <SourceList :sources="sources" />
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
  display: grid;
  min-height: 100vh;
  grid-template-columns: 252px minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 26px;
  border-right: 1px solid #dbe3ee;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 22px 16px;
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
.profile-chip span,
.profile-chip small,
.summary-item span,
.summary-item strong {
  display: block;
}

.brand strong {
  font-size: 15px;
}

.brand span {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

nav {
  display: grid;
  gap: 6px;
}

nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  border-radius: 6px;
  padding: 0 10px;
  color: #475569;
  text-decoration: none;
  font-weight: 650;
  font-size: 14px;
}

nav a.active {
  background: color-mix(in srgb, var(--role-accent) 12%, #ffffff);
  color: var(--role-accent);
}

.signout-button {
  min-height: 40px;
  border: 1px solid #dbe3ee;
  background: #ffffff;
  color: #475569;
}

.security-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  background: #f8fbff;
  padding: 12px;
  color: #1e3a8a;
  font-size: 13px;
  font-weight: 700;
}

.main-area {
  min-width: 0;
  padding: 24px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: #111827;
  font-size: 28px;
  font-weight: 760;
}

.profile-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 218px;
  border: 1px solid #d8dee7;
  border-radius: 6px;
  background: #ffffff;
  padding: 10px 12px;
}

.avatar-chip {
  width: 38px;
  height: 38px;
  background: var(--role-accent);
  font-size: 13px;
}

.profile-chip span {
  font-weight: 760;
}

.profile-chip small {
  margin-top: 2px;
  color: #64748b;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  border: 1px solid #dbe3ee;
  border-radius: 6px;
  background: #ffffff;
  padding: 14px;
}

.summary-item svg {
  color: var(--role-accent);
  flex: 0 0 auto;
}

.summary-item span {
  color: #64748b;
  font-size: 12px;
}

.summary-item strong {
  margin-top: 3px;
  color: #172033;
  font-size: 14px;
}

.role-section {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
  border: 1px solid #dbe3ee;
  border-radius: 6px;
  background: #ffffff;
  padding: 16px;
  margin-bottom: 16px;
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
  color: #64748b;
  font-size: 13px;
}

.status-error {
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #991b1b;
  border-radius: 6px;
  padding: 10px 12px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.8fr);
  gap: 16px;
  align-items: start;
}

.workspace-panel {
  min-width: 0;
  border: 1px solid #dbe3ee;
  border-radius: 6px;
  background: #ffffff;
  padding: 16px;
}

.sources-wrap {
  position: sticky;
  top: 20px;
}

@media (max-width: 1120px) {
  .app-shell {
    grid-template-columns: 82px minmax(0, 1fr);
  }

  .brand div:last-child,
  nav span,
  .security-note span,
  .signout-button span {
    display: none;
  }

  nav a,
  .security-note,
  .signout-button {
    justify-content: center;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace-grid,
  .role-section,
  .login-panel {
    grid-template-columns: 1fr;
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
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
