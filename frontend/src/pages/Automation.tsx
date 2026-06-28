import React, { useEffect, useState } from 'react';
import { serverApi, bulkApi, discoveryApi, schedulerApi } from '../services/api';

interface Server {
  id: string;
  hostname: string | null;
  bmc_ip: string;
  status: string;
}

interface BulkJob {
  id: string;
  name: string;
  job_type: string;
  action: string;
  status: string;
  total_count: number;
  success_count: number;
  fail_count: number;
  created_at: string;
}

interface DiscoveryJob {
  id: string;
  name: string;
  network_range: string;
  ports: number[];
  status: string;
  device_count: number;
  created_at: string;
}

interface ScheduledTask {
  id: string;
  name: string;
  task_type: string;
  schedule: string;
  is_enabled: boolean;
  run_count: number;
  fail_count: number;
  next_run_at: string | null;
  last_run_at: string | null;
}

type TabType = 'bulk' | 'discovery' | 'scheduler';

const Automation: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('bulk');
  const [servers, setServers] = useState<Server[]>([]);

  // Bulk operations state
  const [selectedServers, setSelectedServers] = useState<string[]>([]);
  const [powerAction, setPowerAction] = useState<string>('on');
  const [jobName, setJobName] = useState<string>('');
  const [bulkJobs, setBulkJobs] = useState<BulkJob[]>([]);

  // Discovery state
  const [discoveryName, setDiscoveryName] = useState<string>('');
  const [networkRange, setNetworkRange] = useState<string>('192.168.1.0/24');
  const [discoveryPorts, setDiscoveryPorts] = useState<string>('623,443');
  const [discoveryJobs, setDiscoveryJobs] = useState<DiscoveryJob[]>([]);

  // Scheduler state
  const [taskName, setTaskName] = useState<string>('');
  const [taskType, setTaskType] = useState<string>('power_control');
  const [cronSchedule, setCronSchedule] = useState<string>('0 2 * * *');
  const [taskParams, setTaskParams] = useState<string>('{}');
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadServers();
    loadBulkJobs();
    loadDiscoveryJobs();
    loadScheduledTasks();
  }, []);

  const loadServers = async () => {
    try {
      const response = await serverApi.list();
      setServers(response.data);
    } catch (err) {
      console.error('Failed to load servers:', err);
    }
  };

  const loadBulkJobs = async () => {
    try {
      const response = await bulkApi.listJobs();
      setBulkJobs(response.data);
    } catch (err) {
      console.error('Failed to load bulk jobs:', err);
    }
  };

  const loadDiscoveryJobs = async () => {
    try {
      const response = await discoveryApi.listJobs();
      setDiscoveryJobs(response.data);
    } catch (err) {
      console.error('Failed to load discovery jobs:', err);
    }
  };

  const loadScheduledTasks = async () => {
    try {
      const response = await schedulerApi.listTasks();
      setScheduledTasks(response.data);
    } catch (err) {
      console.error('Failed to load scheduled tasks:', err);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleCreateBulkJob = async () => {
    if (!jobName || selectedServers.length === 0) {
      showMessage('error', 'Please enter job name and select at least one server');
      return;
    }
    if (selectedServers.length > 50) {
      showMessage('error', 'Maximum 50 servers per batch');
      return;
    }

    setLoading(true);
    try {
      await bulkApi.createPowerJob({
        name: jobName,
        action: powerAction,
        target_servers: selectedServers
      });
      showMessage('success', 'Bulk power job created successfully');
      setJobName('');
      setSelectedServers([]);
      loadBulkJobs();
    } catch (err: any) {
      showMessage('error', err.response?.data?.detail || 'Failed to create job');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDiscovery = async () => {
    if (!discoveryName || !networkRange) {
      showMessage('error', 'Please enter name and network range');
      return;
    }

    setLoading(true);
    try {
      const ports = discoveryPorts.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      await discoveryApi.scan({
        name: discoveryName,
        network_range: networkRange,
        ports: ports.length > 0 ? ports : [623, 443]
      });
      showMessage('success', 'Discovery job started');
      setDiscoveryName('');
      loadDiscoveryJobs();
    } catch (err: any) {
      showMessage('error', err.response?.data?.detail || 'Failed to start discovery');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async () => {
    if (!taskName || !cronSchedule || selectedServers.length === 0) {
      showMessage('error', 'Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      const params = JSON.parse(taskParams || '{}');
      await schedulerApi.createTask({
        name: taskName,
        task_type: taskType,
        schedule: cronSchedule,
        parameters: params,
        target_servers: selectedServers
      });
      showMessage('success', 'Scheduled task created');
      setTaskName('');
      setSelectedServers([]);
      loadScheduledTasks();
    } catch (err: any) {
      showMessage('error', err.response?.data?.detail || 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTask = async (taskId: string, currentEnabled: boolean) => {
    try {
      await schedulerApi.updateTask(taskId, { is_enabled: !currentEnabled });
      loadScheduledTasks();
    } catch (err) {
      showMessage('error', 'Failed to update task');
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await schedulerApi.deleteTask(taskId);
      loadScheduledTasks();
    } catch (err) {
      showMessage('error', 'Failed to delete task');
    }
  };

  const handleExecuteTask = async (taskId: string) => {
    try {
      await schedulerApi.executeTask(taskId);
      showMessage('success', 'Task executed');
      loadScheduledTasks();
    } catch (err) {
      showMessage('error', 'Failed to execute task');
    }
  };

  // NOC style theme
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

  const panelStyle: React.CSSProperties = {
    backgroundColor: '#111827',
    borderRadius: '8px',
    padding: '20px',
    margin: '20px'
  };

  const tabContainerStyle: React.CSSProperties = {
    display: 'flex',
    borderBottom: '1px solid #334155',
    marginBottom: '20px'
  };

  const tabStyle = (isActive: boolean): React.CSSProperties => ({
    padding: '12px 24px',
    cursor: 'pointer',
    borderBottom: isActive ? '2px solid #00d4aa' : 'none',
    color: isActive ? '#00d4aa' : '#94a3b8',
    fontWeight: isActive ? 'bold' : 'normal'
  });

  const inputStyle: React.CSSProperties = {
    backgroundColor: '#1e293b',
    color: '#e0e6ed',
    border: '1px solid #334155',
    borderRadius: '4px',
    padding: '8px 12px',
    fontSize: '14px',
    width: '100%',
    marginBottom: '12px'
  };

  const selectStyle: React.CSSProperties = {
    backgroundColor: '#1e293b',
    color: '#e0e6ed',
    border: '1px solid #334155',
    borderRadius: '4px',
    padding: '8px 12px',
    fontSize: '14px',
    width: '100%',
    marginBottom: '12px'
  };

  const buttonStyle: React.CSSProperties = {
    backgroundColor: '#00d4aa',
    color: '#0a0e17',
    border: 'none',
    borderRadius: '4px',
    padding: '10px 20px',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: '14px'
  };

  const secondaryButtonStyle: React.CSSProperties = {
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '6px 12px',
    cursor: 'pointer',
    fontSize: '12px',
    marginRight: '8px'
  };

  const dangerButtonStyle: React.CSSProperties = {
    backgroundColor: '#ef4444',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '6px 12px',
    cursor: 'pointer',
    fontSize: '12px'
  };

  const statusBadge = (status: string): React.CSSProperties => ({
    padding: '4px 12px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 'bold',
    backgroundColor: status === 'completed' || status === 'success' ? '#00d4aa' :
                     status === 'running' ? '#3b82f6' :
                     status === 'failed' ? '#ef4444' : '#64748b',
    color: '#fff'
  });

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <h1 style={{ color: '#00d4aa', margin: 0, fontSize: '24px' }}>
          Automation
        </h1>
        <a href="/" style={{ color: '#00d4aa', textDecoration: 'none' }}>
          ← Back to Dashboard
        </a>
      </header>

      {message && (
        <div style={{
          margin: '20px',
          padding: '12px',
          borderRadius: '4px',
          backgroundColor: message.type === 'success' ? '#064e3b' : '#7f1d1d',
          color: message.type === 'success' ? '#00d4aa' : '#ef4444'
        }}>
          {message.text}
        </div>
      )}

      <div style={panelStyle}>
        <div style={tabContainerStyle}>
          <div style={tabStyle(activeTab === 'bulk')} onClick={() => setActiveTab('bulk')}>
            Bulk Operations
          </div>
          <div style={tabStyle(activeTab === 'discovery')} onClick={() => setActiveTab('discovery')}>
            Auto Discovery
          </div>
          <div style={tabStyle(activeTab === 'scheduler')} onClick={() => setActiveTab('scheduler')}>
            Scheduled Tasks
          </div>
        </div>

        {/* Bulk Operations Tab */}
        {activeTab === 'bulk' && (
          <div>
            <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Bulk Power Control</h3>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Job Name
              </label>
              <input
                type="text"
                style={inputStyle}
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
                placeholder="e.g., Nightly Shutdown"
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Power Action
              </label>
              <select style={selectStyle} value={powerAction} onChange={(e) => setPowerAction(e.target.value)}>
                <option value="on">Power On</option>
                <option value="off">Power Off (Force)</option>
                <option value="restart">Restart (Force)</option>
                <option value="soft_off">Graceful Shutdown</option>
                <option value="soft_restart">Graceful Restart</option>
              </select>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Target Servers ({selectedServers.length} selected, max 50)
              </label>
              <div style={{ maxHeight: '200px', overflowY: 'auto', backgroundColor: '#0a0e17', borderRadius: '4px', padding: '12px' }}>
                {servers.map(server => (
                  <label key={server.id} style={{ display: 'flex', alignItems: 'center', padding: '6px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selectedServers.includes(server.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedServers([...selectedServers, server.id]);
                        } else {
                          setSelectedServers(selectedServers.filter(id => id !== server.id));
                        }
                      }}
                      style={{ marginRight: '8px' }}
                    />
                    <span style={{ color: '#e0e6ed' }}>{server.hostname || server.bmc_ip}</span>
                    <span style={{ color: '#64748b', marginLeft: '8px', fontSize: '12px' }}>({server.bmc_ip})</span>
                  </label>
                ))}
              </div>
            </div>

            <button style={buttonStyle} onClick={handleCreateBulkJob} disabled={loading}>
              {loading ? 'Creating...' : 'Create Bulk Job'}
            </button>

            {/* Bulk Jobs List */}
            <h3 style={{ color: '#00d4aa', marginTop: '32px' }}>Recent Jobs</h3>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {bulkJobs.map(job => (
                <div key={job.id} style={{ backgroundColor: '#0a0e17', padding: '12px', borderRadius: '4px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#e0e6ed', fontWeight: 'bold' }}>{job.name}</div>
                      <div style={{ color: '#64748b', fontSize: '12px' }}>
                        Action: {job.action} | {new Date(job.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div style={statusBadge(job.status)}>{job.status}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '12px' }}>
                    <span style={{ color: '#94a3b8' }}>Total: {job.total_count}</span>
                    <span style={{ color: '#00d4aa' }}>Success: {job.success_count}</span>
                    <span style={{ color: '#ef4444' }}>Failed: {job.fail_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Discovery Tab */}
        {activeTab === 'discovery' && (
          <div>
            <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Network Discovery</h3>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Discovery Name
              </label>
              <input
                type="text"
                style={inputStyle}
                value={discoveryName}
                onChange={(e) => setDiscoveryName(e.target.value)}
                placeholder="e.g., Data Center Scan"
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Network Range (CIDR)
              </label>
              <input
                type="text"
                style={inputStyle}
                value={networkRange}
                onChange={(e) => setNetworkRange(e.target.value)}
                placeholder="e.g., 192.168.1.0/24"
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Ports (comma separated)
              </label>
              <input
                type="text"
                style={inputStyle}
                value={discoveryPorts}
                onChange={(e) => setDiscoveryPorts(e.target.value)}
                placeholder="623,443"
              />
            </div>

            <button style={buttonStyle} onClick={handleCreateDiscovery} disabled={loading}>
              {loading ? 'Starting...' : 'Start Discovery'}
            </button>

            {/* Discovery Jobs List */}
            <h3 style={{ color: '#00d4aa', marginTop: '32px' }}>Discovery Jobs</h3>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {discoveryJobs.map(job => (
                <div key={job.id} style={{ backgroundColor: '#0a0e17', padding: '12px', borderRadius: '4px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#e0e6ed', fontWeight: 'bold' }}>{job.name}</div>
                      <div style={{ color: '#64748b', fontSize: '12px' }}>
                        {job.network_range} | Ports: {job.ports?.join(', ')}
                      </div>
                    </div>
                    <div style={statusBadge(job.status)}>{job.status}</div>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                    Devices found: <span style={{ color: '#00d4aa', fontWeight: 'bold' }}>{job.device_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scheduler Tab */}
        {activeTab === 'scheduler' && (
          <div>
            <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Create Scheduled Task</h3>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Task Name
              </label>
              <input
                type="text"
                style={inputStyle}
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                placeholder="e.g., Daily Sensor Collection"
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Task Type
              </label>
              <select style={selectStyle} value={taskType} onChange={(e) => setTaskType(e.target.value)}>
                <option value="power_control">Power Control</option>
                <option value="sensor_collect">Sensor Collection</option>
                <option value="sel_collect">SEL Log Collection</option>
                <option value="custom_command">Custom Command</option>
              </select>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Cron Schedule
              </label>
              <input
                type="text"
                style={inputStyle}
                value={cronSchedule}
                onChange={(e) => setCronSchedule(e.target.value)}
                placeholder="0 2 * * *"
              />
              <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
                Format: minute hour day month weekday (e.g., 0 2 * * * = daily at 2:00 AM)
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Parameters (JSON)
              </label>
              <textarea
                style={{ ...inputStyle, minHeight: '80px', fontFamily: 'monospace' }}
                value={taskParams}
                onChange={(e) => setTaskParams(e.target.value)}
                placeholder='{"action": "on"} or {"hours": 24}'
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                Target Servers ({selectedServers.length} selected)
              </label>
              <div style={{ maxHeight: '150px', overflowY: 'auto', backgroundColor: '#0a0e17', borderRadius: '4px', padding: '12px' }}>
                {servers.map(server => (
                  <label key={server.id} style={{ display: 'flex', alignItems: 'center', padding: '6px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selectedServers.includes(server.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedServers([...selectedServers, server.id]);
                        } else {
                          setSelectedServers(selectedServers.filter(id => id !== server.id));
                        }
                      }}
                      style={{ marginRight: '8px' }}
                    />
                    <span style={{ color: '#e0e6ed' }}>{server.hostname || server.bmc_ip}</span>
                  </label>
                ))}
              </div>
            </div>

            <button style={buttonStyle} onClick={handleCreateTask} disabled={loading}>
              {loading ? 'Creating...' : 'Create Scheduled Task'}
            </button>

            {/* Scheduled Tasks List */}
            <h3 style={{ color: '#00d4aa', marginTop: '32px' }}>Scheduled Tasks</h3>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {scheduledTasks.map(task => (
                <div key={task.id} style={{ backgroundColor: '#0a0e17', padding: '12px', borderRadius: '4px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#e0e6ed', fontWeight: 'bold' }}>{task.name}</div>
                      <div style={{ color: '#64748b', fontSize: '12px' }}>
                        {task.task_type} | Schedule: {task.schedule}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        backgroundColor: task.is_enabled ? '#00d4aa' : '#64748b',
                        color: '#fff'
                      }}>
                        {task.is_enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                    <span>Runs: {task.run_count}</span>
                    <span style={{ color: task.fail_count > 0 ? '#ef4444' : '#94a3b8' }}>
                      Fails: {task.fail_count}
                    </span>
                    {task.next_run_at && (
                      <span>Next: {new Date(task.next_run_at).toLocaleString()}</span>
                    )}
                  </div>
                  <div style={{ marginTop: '8px' }}>
                    <button style={secondaryButtonStyle} onClick={() => handleExecuteTask(task.id)}>
                      Run Now
                    </button>
                    <button style={secondaryButtonStyle} onClick={() => handleToggleTask(task.id, task.is_enabled)}>
                      {task.is_enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button style={dangerButtonStyle} onClick={() => handleDeleteTask(task.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Automation;