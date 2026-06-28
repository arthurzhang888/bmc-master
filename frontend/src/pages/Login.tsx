import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement actual authentication
    navigate('/');
  };

  const containerStyle: React.CSSProperties = {
    backgroundColor: '#0a0e17',
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const formStyle: React.CSSProperties = {
    backgroundColor: '#111827',
    padding: '40px',
    borderRadius: '8px',
    border: '1px solid #1e3a5f',
    width: '360px'
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px',
    marginBottom: '16px',
    backgroundColor: '#0a0e17',
    border: '1px solid #1e3a5f',
    borderRadius: '4px',
    color: '#e0e6ed',
    fontSize: '14px'
  };

  const buttonStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px',
    backgroundColor: '#00d4aa',
    color: '#0a0e17',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer'
  };

  return (
    <div style={containerStyle}>
      <form onSubmit={handleSubmit} style={formStyle}>
        <h1 style={{ color: '#00d4aa', textAlign: 'center', marginBottom: '8px' }}>
          BMC Master
        </h1>
        <p style={{ color: '#64748b', textAlign: 'center', marginBottom: '32px' }}>
          Server Management System
        </p>

        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={inputStyle}
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={inputStyle}
        />

        <button type="submit" style={buttonStyle}>
          Login
        </button>
      </form>
    </div>
  );
};

export default Login;
