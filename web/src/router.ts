import { createRouter, createWebHistory } from 'vue-router'

const RouteShell = { template: '<span aria-hidden="true"></span>' }

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: RouteShell },
    { path: '/cases/new', name: 'case-new', component: RouteShell },
    { path: '/cases/:caseId', name: 'case-detail', component: RouteShell },
    { path: '/runs/:runId/facts', name: 'run-facts', component: RouteShell },
    { path: '/runs/:runId/results', name: 'run-results', component: RouteShell },
    { path: '/runs/:runId/report', name: 'run-report', component: RouteShell },
  ],
})
