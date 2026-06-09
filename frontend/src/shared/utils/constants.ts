/** Task status display name mapping */
export const TASK_STATUS_MAP: Record<string, string> = {
  queued: '排队中',
  in_progress: '运行中',
  completed: '已完成',
  failed: '失败',
  stopped: '已停止',
  cancelled: '已取消',
}

/** Element Plus tag type */
export type ElTagType = 'info' | 'success' | 'danger' | 'warning' | 'primary' | ''

/** Task status to Element Plus tag type */
export const TASK_STATUS_TAG_TYPE: Record<string, ElTagType> = {
  queued: 'info',
  in_progress: '',
  completed: 'success',
  failed: 'danger',
  stopped: 'warning',
  cancelled: 'warning',
}

/** Task status to custom color override */
export const TASK_STATUS_COLOR: Record<string, string> = {
  queued: '#5f739c',
  in_progress: '#3b82f6',
  completed: '#36e08a',
  failed: '#ff5a6e',
  stopped: '#ffb020',
  cancelled: '#ffb020',
}
