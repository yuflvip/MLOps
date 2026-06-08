import type { RouteRecordRaw } from 'vue-router'

export const templateRoutes: RouteRecordRaw[] = [
  {
    path: 'template',
    name: 'TemplateList',
    component: () => import('./components/TemplateListPage.vue'),
  },
]
