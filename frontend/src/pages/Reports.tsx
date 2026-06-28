import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { reportApi, serverApi } from '../services/api';

interface Server {
  id: string;
  hostname: string | null;
  bmc_ip: string;
}

interface SensorTrendData {
  server_id: string;
  sensor_type: string;
  time_range: string;
  data_points: { timestamp: string; value: number }[];
  statistics: {
    min: number;
    max: number;
    avg: number;
    std_dev: number;
    trend_slope?: number;
  };
}

interface AlertStatistics {
  total_alerts: number;
  by_severity: Record<string, number>;
  by_server: Record<string, number>;
  daily_trend: { date: string; count: number }[];
  period_days: number;
}

interface Anomaly {
  timestamp: string;
  value: number;
  z_score: number;
  severity: string;
}

type ReportType = 'sensor_trend' | 'alert_statistics' | 'anomalies';

const Reports: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [reportType, setReportType] = useState<ReportType>('sensor_trend');
  const [selectedServer, setSelectedServer] = useState<string>('');
  const [sensorType, setSensorType] = useState<string>('temperature');
  const [hours, setHours] = useState<number>(24);
  const [days, setDays] = useState<number>(7);
  const [threshold, setThreshold] = useState<number>(3.0);

  const [sensorData, setSensorData] = useState<SensorTrendData | null>(null);
  const [alertData, setAlertData] = useState<AlertStatistics | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      const response = await serverApi.list();
      setServers(response.data);
      if (response.data.length > 0) {
        setSelectedServer(response.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load servers:', err);
    }
  };

  const generateReport = async () => {
    setLoading(true);
    setError(null);
    try {
      if (reportType === 'sensor_trend') {
        const response = await reportApi.getSensorTrend(selectedServer, sensorType, hours);
        setSensorData(response.data);
      } else if (reportType === 'alert_statistics') {
        const response = await reportApi.getAlertStatistics(days);
        setAlertData(response.data);
      } else if (reportType === 'anomalies') {
        const response = await reportApi.getAnomalies(selectedServer, sensorType, hours, threshold);
        setAnomalies(response.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: string) => {
    try {
      let parameters: any = {};
      if (reportType === 'sensor_trend' || reportType === 'anomalies') {
        parameters = { server_id: selectedServer, sensor_type: sensorType, hours };
      } else if (reportType === 'alert_statistics') {
        parameters = { days };
      }

      const response = await reportApi.export(reportType, parameters, format);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${reportType}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format === 'excel' ? 'xlsx' : format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export failed');
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

  const selectStyle: React.CSSProperties = {
    backgroundColor: '#1e293b',
    color: '#e0e6ed',
    border: '1px solid #334155',
    borderRadius: '4px',
    padding: '8px 12px',
    marginRight: '12px',
    fontSize: '14px'
  };

  const buttonStyle: React.CSSProperties = {
    backgroundColor: '#00d4aa',
    color: '#0a0e17',
    border: 'none',
    borderRadius: '4px',
    padding: '8px 16px',
    cursor: 'pointer',
    fontWeight: 'bold',
    marginRight: '8px'
  };

  const exportButtonStyle: React.CSSProperties = {
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '6px 12px',
    cursor: 'pointer',
    fontSize: '12px',
    marginRight: '8px'
  };

  const getSensorChartOption = () => {
    if (!sensorData || !sensorData.data_points.length) return {};

    return {
      backgroundColor: 'transparent',
      title: {
        text: `${sensorData.sensor_type} Trend - Last ${sensorData.time_range}`,
        textStyle: { color: '#00d4aa', fontSize: 16 },
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1e293b',
        borderColor: '#334155',
        textStyle: { color: '#e0e6ed' }
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: sensorData.data_points.map(p => new Date(p.timestamp).toLocaleTimeString()),
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      series: [{
        name: sensorData.sensor_type,
        type: 'line',
        data: sensorData.data_points.map(p => p.value),
        smooth: true,
        lineStyle: { color: '#00d4aa', width: 2 },
        itemStyle: { color: '#00d4aa' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 212, 170, 0.3)' },
              { offset: 1, color: 'rgba(0, 212, 170, 0.05)' }
            ]
          }
        }
      }]
    };
  };

  const getAlertChartOption = () => {
    if (!alertData) return {};

    return {
      backgroundColor: 'transparent',
      title: {
        text: `Alert Statistics - Last ${alertData.period_days} Days`,
        textStyle: { color: '#00d4aa', fontSize: 16 },
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1e293b',
        borderColor: '#334155',
        textStyle: { color: '#e0e6ed' }
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: alertData.daily_trend.map(d => new Date(d.date).toLocaleDateString()),
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      series: [{
        name: 'Alerts',
        type: 'bar',
        data: alertData.daily_trend.map(d => d.count),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#ef4444' },
              { offset: 1, color: '#7f1d1d' }
            ]
          }
        }
      }]
    };
  };

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <h1 style={{ color: '#00d4aa', margin: 0, fontSize: '24px' }}>
          Reports & Analytics
        </h1>
        <a href="/" style={{ color: '#00d4aa', textDecoration: 'none' }}>
          ← Back to Dashboard
        </a>
      </header>

      {/* Report Controls */}
      <div style={panelStyle}>
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', marginRight: '12px' }}>Report Type:</label>
          <select
            style={selectStyle}
            value={reportType}
            onChange={(e) => setReportType(e.target.value as ReportType)}
          >
            <option value="sensor_trend">Sensor Trend</option>
            <option value="alert_statistics">Alert Statistics</option>
            <option value="anomalies">Anomaly Detection</option>
          </select>
        </div>

        {reportType !== 'alert_statistics' && (
          <div style={{ marginBottom: '16px' }}>
            <label style={{ color: '#94a3b8', marginRight: '12px' }}>Server:</label>
            <select
              style={selectStyle}
              value={selectedServer}
              onChange={(e) => setSelectedServer(e.target.value)}
            >
              {servers.map(s => (
                <option key={s.id} value={s.id}>
                  {s.hostname || s.bmc_ip}
                </option>
              ))}
            </select>

            <label style={{ color: '#94a3b8', marginRight: '12px', marginLeft: '16px' }}>Sensor:</label>
            <select
              style={selectStyle}
              value={sensorType}
              onChange={(e) => setSensorType(e.target.value)}
            >
              <option value="temperature">Temperature</option>
              <option value="voltage">Voltage</option>
              <option value="fan">Fan</option>
              <option value="power">Power</option>
            </select>

            <label style={{ color: '#94a3b8', marginRight: '12px', marginLeft: '16px' }}>Hours:</label>
            <select
              style={selectStyle}
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
            >
              <option value={6}>6 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
              <option value={72}>72 hours</option>
              <option value={168}>1 week</option>
            </select>
          </div>
        )}

        {reportType === 'alert_statistics' && (
          <div style={{ marginBottom: '16px' }}>
            <label style={{ color: '#94a3b8', marginRight: '12px' }}>Period:</label>
            <select
              style={selectStyle}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={1}>1 day</option>
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
            </select>
          </div>
        )}

        {reportType === 'anomalies' && (
          <div style={{ marginBottom: '16px' }}>
            <label style={{ color: '#94a3b8', marginRight: '12px' }}>Z-Score Threshold:</label>
            <select
              style={selectStyle}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
            >
              <option value={2}>2 (More sensitive)</option>
              <option value={3}>3 (Standard)</option>
              <option value={4}>4 (Less sensitive)</option>
              <option value={5}>5 (Very strict)</option>
            </select>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button style={buttonStyle} onClick={generateReport} disabled={loading}>
            {loading ? 'Generating...' : 'Generate Report'}
          </button>

          <div>
            <button style={exportButtonStyle} onClick={() => handleExport('csv')}>
              Export CSV
            </button>
            <button style={exportButtonStyle} onClick={() => handleExport('excel')}>
              Export Excel
            </button>
            <button style={exportButtonStyle} onClick={() => handleExport('pdf')}>
              Export PDF
            </button>
          </div>
        </div>

        {error && (
          <div style={{ color: '#ef4444', marginTop: '12px', padding: '12px', backgroundColor: '#7f1d1d', borderRadius: '4px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Report Results */}
      {sensorData && reportType === 'sensor_trend' && (
        <div style={panelStyle}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Sensor Trend Analysis</h3>

          {/* Statistics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '20px' }}>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#00d4aa' }}>
                {sensorData.statistics.min.toFixed(2)}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Minimum</div>
            </div>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#00d4aa' }}>
                {sensorData.statistics.max.toFixed(2)}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Maximum</div>
            </div>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#00d4aa' }}>
                {sensorData.statistics.avg.toFixed(2)}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Average</div>
            </div>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: sensorData.statistics.trend_slope && sensorData.statistics.trend_slope > 0 ? '#ef4444' : '#00d4aa' }}>
                {sensorData.statistics.trend_slope ? (sensorData.statistics.trend_slope > 0 ? '↗' : '↘') : '-'}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Trend</div>
            </div>
          </div>

          <ReactECharts option={getSensorChartOption()} style={{ height: '350px' }} />
        </div>
      )}

      {alertData && reportType === 'alert_statistics' && (
        <div style={panelStyle}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Alert Statistics</h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px' }}>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ef4444' }}>
                {alertData.total_alerts}
              </div>
              <div style={{ fontSize: '14px', color: '#64748b' }}>Total Alerts</div>
            </div>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px' }}>
              <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '8px' }}>By Severity</div>
              {Object.entries(alertData.by_severity).map(([sev, count]) => (
                <div key={sev} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                  <span style={{ color: '#94a3b8' }}>{sev}:</span>
                  <span style={{ color: '#e0e6ed' }}>{count}</span>
                </div>
              ))}
            </div>
            <div style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '4px' }}>
              <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '8px' }}>Top Servers</div>
              {Object.entries(alertData.by_server).slice(0, 5).map(([srv, count]) => (
                <div key={srv} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                  <span style={{ color: '#94a3b8' }}>{srv.slice(0, 8)}...:</span>
                  <span style={{ color: '#e0e6ed' }}>{count}</span>
                </div>
              ))}
            </div>
          </div>

          <ReactECharts option={getAlertChartOption()} style={{ height: '300px' }} />
        </div>
      )}

      {anomalies.length > 0 && reportType === 'anomalies' && (
        <div style={panelStyle}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>
            Detected Anomalies ({anomalies.length} found)
          </h3>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {anomalies.map((anomaly, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px',
                  backgroundColor: anomaly.severity === 'critical' ? '#7f1d1d' : '#1e293b',
                  borderRadius: '4px',
                  marginBottom: '8px',
                  borderLeft: `4px solid ${anomaly.severity === 'critical' ? '#ef4444' : '#f59e0b'}`
                }}
              >
                <div>
                  <div style={{ color: '#e0e6ed', fontWeight: 'bold' }}>
                    {new Date(anomaly.timestamp).toLocaleString()}
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                    Value: {anomaly.value.toFixed(2)} | Z-Score: {anomaly.z_score.toFixed(2)}
                  </div>
                </div>
                <div style={{
                  padding: '4px 12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  backgroundColor: anomaly.severity === 'critical' ? '#ef4444' : '#f59e0b',
                  color: '#fff'
                }}>
                  {anomaly.severity.toUpperCase()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {anomalies.length === 0 && reportType === 'anomalies' && !loading && (
        <div style={panelStyle}>
          <div style={{ textAlign: 'center', color: '#64748b', padding: '40px' }}>
            No anomalies detected with current threshold
          </div>
        </div>
      )}
    </div>
  );
};

export default Reports;