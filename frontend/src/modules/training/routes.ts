import type { RouteRecordRaw } from 'vue-router'

export const trainingRoutes: RouteRecordRaw[] = [
  {
    path: 'training',
    name: 'TrainingList',
    component: () => import('./components/TaskListPage.vue'),
  },
  {
    path: 'training/:id',
    name: 'TrainingDetail',
    component: () => import('./components/TaskDetailPage.vue'),
    props: true,
  },
]
