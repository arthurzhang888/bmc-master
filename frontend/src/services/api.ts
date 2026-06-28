import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Server API
export const serverApi = {
  list: () => api.get('/api/v1/servers'),
  get: (id: string) => api.get(`/api/v1/servers/${id}`),
  getById: (id: string) => api.get(`/api/v1/servers/${id}`),
  create: (data: any) => api.post('/api/v1/servers', data),
  update: (id: string, data: any) => api.put(`/api/v1/servers/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/servers/${id}`),
  power: (id: string, action: string) =>
    api.post(`/api/v1/servers/${id}/power`, { action }),
  sensors: (id: string) => api.get(`/api/v1/servers/${id}/sensors`),
  getSensors: (id: string) => api.get(`/api/v1/servers/${id}/sensors`),
  getSelLogs: (id: string) => api.get(`/api/v1/servers/${id}/sel`),
};

// Report API
export const reportApi = {
  getSensorTrend: (serverId: string, sensorType: string, hours: number = 24) =>
    api.get('/api/v1/reports/sensor-trend', {
      params: { server_id: serverId, sensor_type: sensorType, hours }
    }),
  getAlertStatistics: (days: number = 7) =>
    api.get('/api/v1/reports/alert-statistics', { params: { days } }),
  getAnomalies: (serverId: string, sensorType: string, hours: number = 24, threshold: number = 3.0) =>
    api.get('/api/v1/reports/anomalies', {
      params: { server_id: serverId, sensor_type: sensorType, hours, threshold }
    }),
  export: (reportType: string, parameters: any, format: string) =>
    api.post('/api/v1/reports/export', { report_type: reportType, parameters, format }, {
      responseType: 'blob'
    }),
};

// Bulk Operations API
export const bulkApi = {
  createPowerJob: (data: { name: string; action: string; target_servers: string[] }) =>
    api.post('/api/v1/bulk/power', data),
  listJobs: (skip: number = 0, limit: number = 100) =>
    api.get('/api/v1/bulk/jobs', { params: { skip, limit } }),
  getJob: (jobId: string) =>
    api.get(`/api/v1/bulk/jobs/${jobId}`),
};

// Discovery API
export const discoveryApi = {
  scan: (data: { name: string; network_range: string; ports: number[] }) =>
    api.post('/api/v1/discovery/scan', data),
  listJobs: (skip: number = 0, limit: number = 100) =>
    api.get('/api/v1/discovery/jobs', { params: { skip, limit } }),
  getJob: (jobId: string) =>
    api.get(`/api/v1/discovery/jobs/${jobId}`),
};

// Scheduler API
export const schedulerApi = {
  createTask: (data: { name: string; task_type: string; schedule: string; parameters: any; target_servers: string[] }) =>
    api.post('/api/v1/scheduler/tasks', data),
  listTasks: (skip: number = 0, limit: number = 100, enabled_only: boolean = false) =>
    api.get('/api/v1/scheduler/tasks', { params: { skip, limit, enabled_only } }),
  getTask: (taskId: string) =>
    api.get(`/api/v1/scheduler/tasks/${taskId}`),
  updateTask: (taskId: string, data: any) =>
    api.put(`/api/v1/scheduler/tasks/${taskId}`, data),
  deleteTask: (taskId: string) =>
    api.delete(`/api/v1/scheduler/tasks/${taskId}`),
  executeTask: (taskId: string) =>
    api.post(`/api/v1/scheduler/tasks/${taskId}/execute`),
  getTaskHistory: (taskId: string, skip: number = 0, limit: number = 100) =>
    api.get(`/api/v1/scheduler/tasks/${taskId}/history`, { params: { skip, limit } }),
};

export default api;
