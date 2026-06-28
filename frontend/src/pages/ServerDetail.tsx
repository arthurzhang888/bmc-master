import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { serverApi } from '../services/api';

interface Server {
  id: string;
  hostname: string | null;
  bmc_ip: string;
  vendor: string | null;
  model: string | null;
  status: string;
  power_state: string;
}

interface Sensor {
  id: string;
  sensor_name: string;
  sensor_type: string;
  value: number;
  unit: string;
  recorded_at: string;
}

interface SELLog {
  id: string;
  timestamp: string;
  sensor_name: string | null;
  event_data: string | null;
  severity: string;
}

const ServerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [server, setServer] = useState<Server | null>(null);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [selLogs, setSelLogs] = useState<SELLog[]>([]);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    if (id) {
      loadServerData();
    }
    // Note: timeRange changes don't trigger reload as historical data filtering
    // requires backend support for time-range queries on sensor history
  }, [id]);

  const loadServerData = async () => {
    try {
      const [serverRes, sensorsRes, selRes] = await Promise.all([
        serverApi.getById(id!),
        serverApi.getSensors(id!),
        serverApi.getSelLogs(id!)
      ]);
      setServer(serverRes.data);
      setSensors(sensorsRes.data);
      setSelLogs(selRes.data);
    } catch (err) {
      console.error('Failed to load server data:', err);
    }
  };

  const containerStyle: React.CSSProperties = {
    backgroundColor: '#0a0e17',
    minHeight: '100vh',
    color: '#e0e6ed',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const chartOption = {
    backgroundColor: 'transparent',
    title: { text: 'Temperature History', textStyle: { color: '#00d4aa' } },
    xAxis: {
      type: 'category',
      data: sensors.filter(s => s.sensor_type === 'Temperature').map(s => s.sensor_name),
      axisLine: { lineStyle: { color: '#64748b' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#64748b' } },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#1e3a5f' } }
    },
    series: [{
      data: sensors.filter(s => s.sensor_type === 'Temperature').map(s => ({
        value: s.value,
        itemStyle: { color: s.value > 80 ? '#ef4444' : s.value > 60 ? '#f59e0b' : '#00d4aa' }
      })),
      type: 'bar',
      barWidth: '50%'
    }],
    grid: { left: '10%', right: '10%', bottom: '15%', top: '20%' }
  };

  if (!server) {
    return <div style={{...containerStyle, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>Loading...</div>;
  }

  return (
    <div style={containerStyle}>
      <header style={{ padding: '16px 24px', borderBottom: '2px solid #00d4aa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ color: '#00d4aa', margin: 0 }}>{server.hostname || server.bmc_ip}</h1>
          <div style={{ color: '#64748b', fontSize: '14px' }}>{server.bmc_ip} | {server.vendor} {server.model}</div>
        </div>
        <Link to="/servers" style={{ color: '#00d4aa', textDecoration: 'none' }}>← Back to Servers</Link>
      </header>

      <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Sensor Charts */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h3 style={{ color: '#00d4aa', margin: 0 }}>Temperature Sensors</h3>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={{ padding: '8px', backgroundColor: '#0a0e17', color: '#e0e6ed', border: '1px solid #1e3a5f', borderRadius: '4px' }}
              title="Time range filtering requires historical data API (not yet implemented)"
            >
              <option value="1h">Last 1 hour (live)</option>
              <option value="24h">Last 24 hours (live)</option>
              <option value="7d">Last 7 days (live)</option>
            </select>
          </div>
          <ReactECharts option={chartOption} style={{ height: '300px' }} />
        </div>

        {/* Current Sensors */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px' }}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Current Readings</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
            {sensors.map(sensor => (
              <div key={sensor.id} style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '8px' }}>
                <div style={{ color: '#64748b', fontSize: '12px' }}>{sensor.sensor_name}</div>
                <div style={{ color: sensor.value > 80 ? '#ef4444' : sensor.value > 60 ? '#f59e0b' : '#00d4aa', fontSize: '24px', fontWeight: 'bold' }}>
                  {sensor.value} <span style={{ fontSize: '14px' }}>{sensor.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SEL Logs */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px', gridColumn: '1 / -1' }}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>System Event Logs (SEL)</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #1e3a5f' }}>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Time</th>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Sensor</th>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Event</th>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Severity</th>
              </tr>
            </thead>
            <tbody>
              {selLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                    No SEL logs available
                  </td>
                </tr>
              ) : (
                selLogs.map(log => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #1e3a5f' }}>
                    <td style={{ padding: '12px' }}>{new Date(log.timestamp).toLocaleString()}</td>
                    <td style={{ padding: '12px' }}>{log.sensor_name}</td>
                    <td style={{ padding: '12px' }}>{log.event_data}</td>
                    <td style={{ padding: '12px', color: log.severity === 'critical' ? '#ef4444' : log.severity === 'warning' ? '#f59e0b' : '#00d4aa' }}>
                      {log.severity}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ServerDetail;
