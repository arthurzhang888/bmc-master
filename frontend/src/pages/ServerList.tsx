import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { serverApi } from '../services/api';

interface Server {
  id: string;
  hostname: string | null;
  bmc_ip: string;
  vendor: string | null;
  model: string | null;
  status: 'online' | 'offline' | 'error';
  power_state: 'on' | 'off' | 'unknown';
  protocol: string;
}

const ServerList: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      const response = await serverApi.list();
      setServers(response.data);
    } catch (err) {
      console.error('Failed to load servers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePowerAction = async (id: string, action: string) => {
    try {
      await serverApi.power(id, action);
      loadServers();
    } catch (err) {
      console.error('Power action failed:', err);
    }
  };

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

  const tableStyle: React.CSSProperties = {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '20px'
  };

  const thStyle: React.CSSProperties = {
    textAlign: 'left',
    padding: '12px',
    borderBottom: '2px solid #1e3a5f',
    color: '#00d4aa',
    fontWeight: '600'
  };

  const tdStyle: React.CSSProperties = {
    padding: '12px',
    borderBottom: '1px solid #1e3a5f'
  };

  const buttonStyle = (color: string): React.CSSProperties => ({
    backgroundColor: color,
    color: '#0a0e17',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '4px',
    cursor: 'pointer',
    marginRight: '8px',
    fontSize: '12px',
    fontWeight: 'bold'
  });

  if (loading) {
    return <div style={containerStyle}>Loading...</div>;
  }

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <h1 style={{ color: '#00d4aa', margin: 0 }}>BMC Master - Servers</h1>
        <nav>
          <Link to="/" style={{ color: '#00d4aa', textDecoration: 'none' }}>
            Back to Dashboard
          </Link>
        </nav>
      </header>

      <div style={{ padding: '24px' }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Hostname</th>
              <th style={thStyle}>IP Address</th>
              <th style={thStyle}>Vendor</th>
              <th style={thStyle}>Model</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Power</th>
              <th style={thStyle}>Protocol</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {servers.map(server => (
              <tr key={server.id}>
                <td style={tdStyle}>{server.hostname || '-'}</td>
                <td style={tdStyle}>{server.bmc_ip}</td>
                <td style={tdStyle}>{server.vendor || '-'}</td>
                <td style={tdStyle}>{server.model || '-'}</td>
                <td style={tdStyle}>
                  <span style={{
                    color: server.status === 'online' ? '#00d4aa' :
                           server.status === 'error' ? '#ef4444' : '#64748b'
                  }}>
                    {server.status}
                  </span>
                </td>
                <td style={tdStyle}>
                  <span style={{
                    color: server.power_state === 'on' ? '#00d4aa' :
                           server.power_state === 'off' ? '#ef4444' : '#64748b'
                  }}>
                    {server.power_state}
                  </span>
                </td>
                <td style={tdStyle}>{server.protocol}</td>
                <td style={tdStyle}>
                  <Link to={`/servers/${server.id}`} style={{ textDecoration: 'none' }}>
                    <button style={buttonStyle('#3b82f6')}>View</button>
                  </Link>
                  <button
                    style={buttonStyle('#00d4aa')}
                    onClick={() => handlePowerAction(server.id, 'on')}
                  >
                    Power On
                  </button>
                  <button
                    style={buttonStyle('#ef4444')}
                    onClick={() => handlePowerAction(server.id, 'off')}
                  >
                    Power Off
                  </button>
                  <button
                    style={buttonStyle('#f59e0b')}
                    onClick={() => handlePowerAction(server.id, 'restart')}
                  >
                    Restart
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ServerList;
