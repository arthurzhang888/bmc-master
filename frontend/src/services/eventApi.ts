import api from './api';

export const eventApi = {
  list: (params?: { event_type?: string; severity?: string; status?: string }) =>
    api.get('/api/v1/events', { params }),
  acknowledge: (id: string, status: string) =>
    api.post(`/api/v1/events/${id}/ack`, { status }),
};
