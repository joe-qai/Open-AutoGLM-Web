import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle,
  ListTodo,
  Clock,
  ArrowRight,
  Play,
  CheckCircle2,
  XCircle,
  Loader2
} from 'lucide-react';
import { useDeviceStore } from '../../stores/deviceStore';
import { useTaskStore } from '../../stores/taskStore';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export function Dashboard() {
  const { devices, fetchDevices } = useDeviceStore();
  const { tasks, fetchTasks } = useTaskStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchDevices();
    fetchTasks();
  }, []);

  // 设备去重：同一设备可能同时通过USB和WiFi连接，按设备名称去重并统计连接类型
  const uniqueDeviceNames = [...new Set(devices.map(d => d.name))];
  const usbCount = devices.filter(d => d.connection_type === 'usb').length;
  const wifiCount = devices.filter(d => d.connection_type === 'tcpip').length;

  const stats = [
    {
      title: '运行中任务',
      value: tasks.filter(t => t.status === 'running').length.toString(),
      icon: <Play className="w-5 h-5 text-blue-400" />,
      trend: '',
      trendUp: true,
    },
    {
      title: '通过率',
      value: tasks.length > 0 
        ? `${Math.round((tasks.filter(t => t.status === 'completed').length / tasks.length) * 100)}%`
        : '0%',
      icon: <CheckCircle className="w-5 h-5 text-green-400" />,
      trend: '',
      trendUp: true,
    },
    {
      title: '总任务数',
      value: tasks.length.toString(),
      icon: <ListTodo className="w-5 h-5 text-purple-400" />,
      trend: '',
      trendUp: true,
    },
    {
      title: '设备数量',
      value: uniqueDeviceNames.length.toString(),
      detail: `USB ${usbCount} | WiFi ${wifiCount}`,
      icon: <Clock className="w-5 h-5 text-orange-400" />,
      trend: '',
      trendUp: true,
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '通过';
      case 'running':
        return '运行中';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">欢迎回来，管理员</h1>
          <p className="text-[#94a3b8] mt-1">今天是个好日子，开始自动化测试吧！</p>
        </div>
        <div className="text-right">
          <p className="text-[#94a3b8] text-sm">{new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <div
            key={index}
            className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 hover:border-[#475569] transition-colors"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[#94a3b8] text-sm">{stat.title}</p>
                <p className="text-2xl font-bold text-white mt-2">{stat.value}</p>
              </div>
              <div className="p-2 bg-[#0f172a] rounded-lg">{stat.icon}</div>
            </div>
            <div className="flex items-center gap-1 mt-4">
              <span className={`text-sm ${stat.trendUp ? 'text-green-400' : 'text-red-400'}`}>
                {stat.trend}
              </span>
              <span className="text-[#64748b] text-sm">较上周</span>
            </div>
              {stat.detail && (
                <p className="text-[#94a3b8] text-xs mt-1">{stat.detail}</p>
              )}
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Task Trend */}
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">任务趋势 (近7天)</h3>
          {tasks.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#fff' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={{ fill: '#6366f1' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-[#64748b]">
              暂无任务数据
            </div>
          )}
        </div>

        {/* Device Status */}
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">设备状态分布</h3>
          {devices.length > 0 ? (
            <div className="h-64 flex items-center">
              <ResponsiveContainer width="50%" height="100%">
                <PieChart>
                  <Pie
                    data={devices.map(d => ({ name: d.platform, value: 1 }))}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    dataKey="value"
                  >
                    {devices.map((device, index) => (
                      <Cell key={`cell-${index}`} fill={device.platform === 'android' ? '#3ddc84' : device.platform === 'ios' ? '#ffffff' : '#007dff'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-3">
                {uniqueDeviceNames.map(name => {
                  const deviceEntries = devices.filter(d => d.name === name);
                  const usbConns = deviceEntries.filter(d => d.connection_type === 'usb').length;
                  const wifiConns = deviceEntries.filter(d => d.connection_type === 'tcpip').length;
                  return (
                    <div key={name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: deviceEntries[0].platform === 'android' ? '#3ddc84' : deviceEntries[0].platform === 'ios' ? '#ffffff' : '#007dff' }}
                        />
                        <span className="text-[#94a3b8]">{name}</span>
                      </div>
                      <span className="text-white font-medium text-xs">
                        {usbConns > 0 && `USB:${usbConns}`} {wifiConns > 0 && `WiFi:${wifiConns}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-[#64748b]">
              暂无设备数据
            </div>
          )}
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-[#334155]">
          <h3 className="text-white font-semibold">最近任务</h3>
          <button 
            onClick={() => navigate('/tasks')}
            className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1 cursor-pointer"
          >
            查看全部 <ArrowRight size={16} />
          </button>
        </div>
        {tasks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-[#64748b] text-sm border-b border-[#334155]">
                  <th className="text-left py-3 px-5 font-medium">任务名称</th>
                  <th className="text-left py-3 px-5 font-medium">设备</th>
                  <th className="text-left py-3 px-5 font-medium">状态</th>
                  <th className="text-left py-3 px-5 font-medium">创建时间</th>
                </tr>
              </thead>
              <tbody>
                {tasks.slice(0, 5).map((task) => (
                  <tr key={task.task_id} className="border-b border-[#334155] last:border-0 hover:bg-[#334155]/30">
                    <td className="py-3 px-5 text-white">{task.name}</td>
                    <td className="py-3 px-5 text-[#94a3b8]">{task.device_id}</td>
                    <td className="py-3 px-5">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(task.status)}
                        <span className={`text-sm ${
                          task.status === 'completed' ? 'text-green-400' :
                          task.status === 'running' ? 'text-blue-400' :
                          task.status === 'failed' ? 'text-red-400' : 'text-[#94a3b8]'
                        }`}>
                          {getStatusText(task.status)}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-5 text-[#94a3b8]">
                      {new Date(task.created_at).toLocaleString('zh-CN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-20">
            <ListTodo className="w-16 h-16 text-[#475569] mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无任务</h3>
            <p className="text-[#64748b]">在Agent页面生成您的第一个脚本任务</p>
          </div>
        )}
      </div>
    </div>
  );
}
