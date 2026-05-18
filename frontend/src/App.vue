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
  Shield,
  UsersRound,
} from '@lucide/vue'
import ChatBox from './components/ChatBox.vue'
import RoleSelector from './components/RoleSelector.vue'
import SourceList from './components/SourceList.vue'
import { getServiceStatus } from './services/api'

const selectedRole = ref('employee')
const sources = ref([])
const status = ref(null)
const statusError = ref('')

const employee = {
  name: 'Sara Khan',
  title: 'Product Engineer',
  department: 'Engineering',
  location: 'Berlin',
  manager: 'Maya Chen',
}

const accessSummary = computed(() => {
  const labels = {
    employee: 'General documents and HR policies',
    hr: 'General documents and HR policies',
    finance: 'General documents and finance reports',
    executive: 'All indexed company departments',
  }
  return labels[selectedRole.value] || 'General company documents'
})

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
  <div class="app-shell">
    <aside class="sidebar" aria-label="Primary navigation">
      <div class="brand">
        <div class="brand-mark">
          <Building2 :size="22" aria-hidden="true" />
        </div>
        <div>
          <strong>Acme Intranet</strong>
          <span>Secure AI Portal</span>
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

      <div class="security-note">
        <Shield :size="18" aria-hidden="true" />
        <span>RBAC filtering active</span>
      </div>
    </aside>

    <main class="main-area">
      <header class="topbar">
        <div>
          <p class="eyebrow">Internal employee workspace</p>
          <h1>AI Knowledge Assistant</h1>
        </div>
        <div class="profile-chip">
          <span>{{ employee.name }}</span>
          <small>{{ employee.department }}</small>
        </div>
      </header>

      <section class="summary-grid" aria-label="Workspace summary">
        <div class="summary-item">
          <BadgeCheck :size="20" aria-hidden="true" />
          <div>
            <span>Signed in as</span>
            <strong>{{ employee.title }}</strong>
          </div>
        </div>
        <div class="summary-item">
          <Shield :size="20" aria-hidden="true" />
          <div>
            <span>Current access</span>
            <strong>{{ accessSummary }}</strong>
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
            <span>Manager</span>
            <strong>{{ employee.manager }}</strong>
          </div>
        </div>
      </section>

      <section class="role-section">
        <div>
          <h2>Access Context</h2>
          <p>Choose the role context for this local demo session.</p>
        </div>
        <RoleSelector v-model="selectedRole" />
      </section>

      <p v-if="statusError" class="status-error">{{ statusError }}</p>

      <section class="workspace-grid">
        <div class="workspace-panel chat-wrap">
          <ChatBox :role="selectedRole" @sources-updated="updateSources" />
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
  background: #f3f6fa;
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

.app-shell {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 252px minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 26px;
  border-right: 1px solid #dbe3ee;
  background: #ffffff;
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
  background: #14355f;
  color: #ffffff;
}

.brand strong,
.brand span {
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
  background: #eef6ff;
  color: #1f6feb;
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
  min-width: 176px;
  border: 1px solid #d8dee7;
  border-radius: 6px;
  background: #ffffff;
  padding: 10px 12px;
  text-align: right;
}

.profile-chip span,
.profile-chip small {
  display: block;
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
  color: #1f6feb;
  flex: 0 0 auto;
}

.summary-item span,
.summary-item strong {
  display: block;
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
  .security-note span {
    display: none;
  }

  nav a,
  .security-note {
    justify-content: center;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace-grid,
  .role-section {
    grid-template-columns: 1fr;
  }

  .sources-wrap {
    position: static;
  }
}

@media (max-width: 700px) {
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

  .profile-chip {
    text-align: left;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
