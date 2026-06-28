import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { serverApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

interface Server {
  id: string;
  hostname: string | null;
  bmc_ip: string;
  status: 'online' | 'offline' | 'error';
  power_state: 'on' | 'off' | 'unknown';
}

const Dashboard: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [stats, setStats] = useState({ online: 0, offline: 0, error: 0 });
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Load initial data
  useEffect(() => {
    loadServers();
  }, []);

  // WebSocket for real-time updates
  useWebSocket(
    (data) => {
      if (data.type === 'sensor_update') {
        // Update last update time
        setLastUpdate(new Date());
      } else if (data.type === 'server_status') {
        // Refresh server list when status changes
        loadServers();
      }
    },
    () => console.log('Connected to real-time updates'),
    () => console.log('Disconnected from real-time updates')
  );

  const loadServers = async () => {
    try {
      const response = await serverApi.list();
      const data = response.data;
      setServers(data);

      // Calculate stats
      const online = data.filter((s: Server) => s.status === 'online').length;
      const offline = data.filter((s: Server) => s.status === 'offline').length;
      const error = data.filter((s: Server) => s.status === 'error').length;
      setStats({ online, offline, error });
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to load servers:', err);
    } finally {
      setLoading(false);
    }
  };

  // NOC style dark theme chart options
  const chartOption = {
    backgroundColor: 'transparent',
    title: {
      text: 'Server Status Overview',
      textStyle: { color: '#00d4aa', fontSize: 16 },
      left: 'center'
    },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#0a0e17',
        borderWidth: 2
      },
      label: {
        show: true,
        color: '#e0e6ed'
      },
      data: [
        { value: stats.online, name: 'Online', itemStyle: { color: '#00d4aa' } },
        { value: stats.offline, name: 'Offline', itemStyle: { color: '#64748b' } },
        { value: stats.error, name: 'Error', itemStyle: { color: '#ef4444' } }
      ]
    }]
  };

  // NOC style color scheme
  const containerStyle: React.CSSProperties = {
    backgroundColor: '#0a0e17',
    minHeight: '100vh',
    color: '#e0e6ed',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const headerStyle: React.CSSProperties = {
    padding: '16px 24px',
    borderBottom: '2px solid #00d4aa',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const statsGridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
    padding: '24px'
  };

  const statCardStyle = (color: string): React.CSSProperties => ({
    backgroundColor: '#111827',
    padding: '24px',
    borderRadius: '8px',
    borderLeft: `4px solid ${color}`,
    textAlign: 'center'
  });

  if (loading) {
    return <div style={containerStyle}>Loading...</div>;
  }

  return (
    <div style={containerStyle}>
      {/* Header with connection status */}
      <header style={headerStyle}>
        <h1 style={{ color: '#00d4aa', margin: 0, fontSize: '24px' }}>
          BMC Master
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {lastUpdate && (
            <span style={{ color: '#64748b', fontSize: '12px' }}>
              Last update: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <nav>
            <Link to="/servers" style={{ color: '#00d4aa', textDecoration: 'none', marginRight: '20px' }}>
              Servers
            </Link>
            <Link to="/reports" style={{ color: '#00d4aa', textDecoration: 'none', marginRight: '20px' }}>
              Reports
            </Link>
            <Link to="/automation" style={{ color: '#00d4aa', textDecoration: 'none', marginRight: '20px' }}>
              Automation
            </Link>
            <Link to="/login" style={{ color: '#64748b', textDecoration: 'none' }}>
              Logout
            </Link>
          </nav>
        </div>
      </header>

      {/* Stats Cards */}
      <div style={statsGridStyle}>
        <div style={statCardStyle('#00d4aa')}>
          <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#00d4aa' }}>
            {stats.online}
          </div>
          <div style={{ fontSize: '14px', color: '#64748b', marginTop: '8px' }}>
            Online Servers
          </div>
        </div>
        <div style={statCardStyle('#64748b')}>
          <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#64748b' }}>
            {stats.offline}
          </div>
          <div style={{ fontSize: '14px', color: '#64748b', marginTop: '8px' }}>
            Offline Servers
          </div>
        </div>
        <div style={statCardStyle('#ef4444')}>
          <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#ef4444' }}>
            {stats.error}
          </div>
          <div style={{ fontSize: '14px', color: '#64748b', marginTop: '8px' }}>
            Error State
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ padding: '0 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px' }}>
          <ReactECharts option={chartOption} style={{ height: '300px' }} />
        </div>

        {/* Recent Servers List */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px' }}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Recent Servers</h3>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {servers.slice(0, 10).map(server => (
              <div
                key={server.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '12px',
                  borderBottom: '1px solid #1e3a5f',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ color: '#e0e6ed' }}>
                    {server.hostname || server.bmc_ip}
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>
                    {server.bmc_ip}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: server.status === 'online' ? '#00d4aa' :
                                    server.status === 'error' ? '#ef4444' : '#64748b'
                  }} />
                  <span style={{
                    color: server.status === 'online' ? '#00d4aa' :
                           server.status === 'error' ? '#ef4444' : '#64748b',
                    fontSize: '12px',
                    textTransform: 'capitalize'
                  }}>
                    {server.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
