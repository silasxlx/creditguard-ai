<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { health, listCases } from './api'
import type { CaseSummary, DemoRole } from './types'

const role = ref<DemoRole>('RM')
const userId = ref('demo-rm')
const cases = ref<CaseSummary[]>([])
const serviceStatus = ref('连接检查中')
const loading = ref(false)

function switchRole(value: DemoRole) {
  role.value = value
  userId.value = value === 'RM' ? 'demo-rm' : 'demo-reviewer'
  loadCases()
}

function onRoleChange(value: string | number) {
  if (value === 'RM' || value === 'REVIEWER') switchRole(value)
}

async function loadCases() {
  loading.value = true
  try {
    cases.value = (await listCases(userId.value)).items
  } catch (error) {
    ElMessage.error(`案件列表加载失败：${String(error)}`)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const result = await health()
    serviceStatus.value = `${result.service} ${result.version} · ${result.status}`
  } catch {
    serviceStatus.value = 'API 未连接'
  }
  await loadCases()
})
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">CREDITGUARD AI · POC</p>
        <h1>授信智能合规审查工作台</h1>
      </div>
      <div class="role-switch">
        <span>当前角色</span>
        <el-segmented
          :model-value="role"
          :options="['RM', 'REVIEWER']"
          @change="onRoleChange"
        />
      </div>
    </header>

    <section class="status-card">
      <div>
        <span class="label">运行状态</span>
        <strong>{{ serviceStatus }}</strong>
      </div>
      <el-button :loading="loading" type="primary" plain @click="loadCases">刷新案件</el-button>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <span class="label">案件总览</span>
          <h2>最近案件</h2>
        </div>
        <el-tag>{{ cases.length }} 个案件</el-tag>
      </div>
      <el-empty v-if="!loading && cases.length === 0" description="暂无案件，等待从 API 创建" />
      <el-table v-else v-loading="loading" :data="cases" stripe>
        <el-table-column prop="case_no" label="案件编号" />
        <el-table-column prop="customer_name" label="客户名称" />
        <el-table-column prop="review_date" label="审查日期" />
        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column label="创建人">
          <template #default="scope">{{ scope.row.created_by }}</template>
        </el-table-column>
      </el-table>
    </section>
  </main>
</template>
