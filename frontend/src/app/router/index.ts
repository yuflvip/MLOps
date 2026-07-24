import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/training',
    children: [
      {
        path: 'training',
        name: 'TrainingList',
        component: () => import('@/modules/training/components/TaskListPage.vue'),
      },
      {
        path: 'training/:id',
        name: 'TrainingDetail',
        component: () => import('@/modules/training/components/TaskDetailPage.vue'),
        props: true,
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/modules/project/components/ProjectListPage.vue'),
      },
      {
        path: 'datasets',
        name: 'DatasetList',
        component: () => import('@/modules/dataset/components/DatasetListPage.vue'),
      },
      {
        path: 'quantization-datasets',
        name: 'QuantizationDatasetList',
        component: () =>
          import('@/modules/quantization-dataset/components/QuantizationDatasetListPage.vue'),
      },
      {
        path: 'quantization-datasets/:id',
        name: 'QuantizationDatasetDetail',
        component: () =>
          import('@/modules/quantization-dataset/components/QuantizationDatasetDetailPage.vue'),
      },
      {
        path: 'runtime-environments',
        name: 'RuntimeEnvironmentList',
        component: () =>
          import('@/modules/runtime-environment/components/RuntimeEnvironmentListPage.vue'),
      },
      {
        path: 'template',
        name: 'TemplateList',
        component: () => import('@/modules/template/components/TemplateListPage.vue'),
      },
      {
        path: 'model-registry',
        name: 'ModelRegistry',
        component: () => import('@/modules/model-registry/components/ModelRegistryPage.vue'),
      },
      {
        path: 'model-registry/exps/:id',
        name: 'ExpDetail',
        component: () => import('@/modules/model-registry/components/ExpDetailPage.vue'),
        props: true,
      },
      {
        path: 'auth',
        name: 'Auth',
        component: () => import('@/shared/components/PlaceholderPage.vue'),
        props: { title: '用户管理' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
