import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { eventApi } from '../services/eventApi';

interface Event {
  id: string;
  event_type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string | null;
  status: 'new' | 'acknowledged' | 'resolved' | 'ignored';
  created_at: string;
}

const EventCenter: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ severity: '', status: '' });

  useEffect(() => {
    loadEvents();
  }, [filter]);

  const loadEvents = async () => {
    try {
      const params: any = {};
      if (filter.severity) params.severity = filter.severity;
      if (filter.status) params.status = filter.status;

      const response = await eventApi.list(params);
      setEvents(response.data);
    } catch (err) {
      console.error('Failed to load events:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (id: string, status: string) => {
    try {
      await eventApi.acknowledge(id, status);
      loadEvents();
    } catch (err) {
      console.error('Failed to update event:', err);
    }
  };

  // NOC style (same as Dashboard)
  const containerStyle: React.CSSProperties = {
    backgroundColor: '#0a0e17',
    minHeight: '100vh',
    color: '#e0e6ed',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'warning': return '#f59e0b';
      default: return '#00d4aa';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return '#ef4444';
      case 'acknowledged': return '#f59e0b';
      case 'resolved': return '#00d4aa';
      default: return '#64748b';
    }
  };

  return (
    <div style={containerStyle}>
      <header style={{ padding: '16px 24px', borderBottom: '2px solid #00d4aa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ color: '#00d4aa', margin: 0 }}>Event Center</h1>
        <Link to="/" style={{ color: '#00d4aa', textDecoration: 'none' }}>← Dashboard</Link>
      </header>

      <div style={{ padding: '24px' }}>
        {/* Filters */}
        <div style={{ marginBottom: '20px', display: 'flex', gap: '16px' }}>
          <select
            value={filter.severity}
            onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
            style={{ padding: '8px', backgroundColor: '#111827', color: '#e0e6ed', border: '1px solid #1e3a5f', borderRadius: '4px' }}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>

          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            style={{ padding: '8px', backgroundColor: '#111827', color: '#e0e6ed', border: '1px solid #1e3a5f', borderRadius: '4px' }}
          >
            <option value="">All Status</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>

        {/* Events Table */}
        <div style={{ backgroundColor: '#111827', borderRadius: '8px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#1e3a5f' }}>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Time</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Severity</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Title</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map(event => (
                <tr key={event.id} style={{ borderBottom: '1px solid #1e3a5f' }}>
                  <td style={{ padding: '12px', color: '#64748b' }}>
                    {new Date(event.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      color: getSeverityColor(event.severity),
                      textTransform: 'uppercase',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      {event.severity}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ color: '#e0e6ed' }}>{event.title}</div>
                    {event.message && (
                      <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
                        {event.message}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      color: getStatusColor(event.status),
                      textTransform: 'capitalize'
                    }}>
                      {event.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    {event.status === 'new' && (
                      <button
                        onClick={() => handleAcknowledge(event.id, 'acknowledged')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#f59e0b',
                          color: '#0a0e17',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          marginRight: '8px'
                        }}
                      >
                        Ack
                      </button>
                    )}
                    {(event.status === 'new' || event.status === 'acknowledged') && (
                      <button
                        onClick={() => handleAcknowledge(event.id, 'resolved')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#00d4aa',
                          color: '#0a0e17',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default EventCenter;
