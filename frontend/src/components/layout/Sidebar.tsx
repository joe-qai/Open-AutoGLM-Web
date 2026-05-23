import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  Package,
  Bot,
  FileCode,
  Smartphone,
  ListTodo,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  FileText,
  FileText as LogIcon
} from 'lucide-react';
import { useState } from 'react';

interface NavGroup {
  type: 'group';
  label: string;
  icon: React.ReactNode;
  children: { path: string; label: string; icon: React.ReactNode }[];
}

interface NavSingle {
  type: 'single';
  path: string;
  label: string;
  icon: React.ReactNode;
}

type NavEntry = NavSingle | NavGroup;

const navEntries: NavEntry[] = [
  { type: 'single', path: '/', label: '仪表盘', icon: <LayoutDashboard size={20} /> },
  {
    type: 'group',
    label: '资源管理',
    icon: <FolderKanban size={20} />,
    children: [
      { path: '/projects', label: '项目管理', icon: <FolderKanban size={20} /> },
      { path: '/apk', label: 'APK管理', icon: <Package size={20} /> },
      { path: '/devices', label: '设备管理', icon: <Smartphone size={20} /> },
    ],
  },
  { type: 'single', path: '/agent', label: 'Agent脚本', icon: <Bot size={20} /> },
  { type: 'single', path: '/scripts', label: '脚本管理', icon: <FileCode size={20} /> },
  {
    type: 'group',
    label: '执行中心',
    icon: <ListTodo size={20} />,
    children: [
      { path: '/tasks', label: '任务管理', icon: <ListTodo size={20} /> },
      { path: '/reports', label: '报告管理', icon: <FileText size={20} /> },
    ],
  },
  { type: 'single', path: '/logs', label: '日志中心', icon: <LogIcon size={20} /> },
  { type: 'single', path: '/settings', label: '设置', icon: <Settings size={20} /> },
];

export function Sidebar() {
  useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['资源管理', '执行中心']));

  const toggleGroup = (label: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-[#1e293b] border-r border-[#334155] transition-all duration-300 z-50 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-[#334155]">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Bot size={18} className="text-white" />
            </div>
            <span className="font-semibold text-white">LOCKIN</span>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto">
            <Bot size={18} className="text-white" />
          </div>
        )}
      </div>

      {/* Toggle Button */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-[#334155] rounded-full flex items-center justify-center text-[#94a3b8] hover:text-white transition-colors border border-[#475569]"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Navigation */}
      <nav className="p-3 space-y-1">
        {navEntries.map((entry) => {
          if (entry.type === 'single') {
            return (
              <NavLink
                key={entry.path}
                to={entry.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-[#94a3b8] hover:bg-[#334155] hover:text-white'
                  } ${collapsed ? 'justify-center' : ''}`
                }
                title={collapsed ? entry.label : undefined}
              >
                <span className="flex-shrink-0">{entry.icon}</span>
                {!collapsed && <span className="text-sm font-medium">{entry.label}</span>}
              </NavLink>
            );
          }

          const isExpanded = expandedGroups.has(entry.label);
          return (
            <div key={entry.label}>
              <button
                onClick={() => toggleGroup(entry.label)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                  collapsed ? 'justify-center' : ''
                } text-[#94a3b8] hover:bg-[#334155] hover:text-white`}
                title={collapsed ? entry.label : undefined}
              >
                <span className="flex-shrink-0">{entry.icon}</span>
                {!collapsed && (
                  <>
                    <span className="text-sm font-medium flex-1 text-left">{entry.label}</span>
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </>
                )}
              </button>
              {!collapsed && isExpanded && (
                <div className="ml-2 mt-1 space-y-1 border-l border-[#334155] pl-2">
                  {entry.children.map((child) => (
                    <NavLink
                      key={child.path}
                      to={child.path}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group ${
                          isActive
                            ? 'bg-indigo-600/50 text-white'
                            : 'text-[#94a3b8] hover:bg-[#334155] hover:text-white'
                        }`
                      }
                    >
                      <span className="flex-shrink-0">{child.icon}</span>
                      <span className="text-sm">{child.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Version */}
      {!collapsed && (
        <div className="absolute bottom-4 left-4 right-4 text-xs text-[#64748b] text-center">
          v1.0.0
        </div>
      )}
    </aside>
  );
}
