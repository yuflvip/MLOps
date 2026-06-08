/** Task status display name mapping */
export const TASK_STATUS_MAP: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

/** Task status to Element Plus tag type */
export const TASK_STATUS_TAG_TYPE: Record<string, string> = {
  queued: 'info',
  running: '',
  succeeded: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

/** Task status to custom color override */
export const TASK_STATUS_COLOR: Record<string, string> = {
  queued: '#5f739c',
  running: '#3b82f6',
  succeeded: '#36e08a',
  failed: '#ff5a6e',
  cancelled: '#ffb020',
}
