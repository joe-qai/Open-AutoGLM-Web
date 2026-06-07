import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  Package,
  Bot,
  FileCode,
  ListTodo,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  FileText,
  Settings,
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
  { type: 'single', path: '/', label: '仪表盘', icon: <LayoutDashboard size={18} /> },
  {
    type: 'group',
    label: '资源管理',
    icon: <FolderKanban size={18} />,
    children: [
      { path: '/projects', label: '项目管理', icon: <FolderKanban size={16} /> },
      { path: '/apk', label: 'APK管理', icon: <Package size={16} /> },
    ],
  },
  { type: 'single', path: '/agent', label: 'AI Agent', icon: <Bot size={18} /> },
  { type: 'single', path: '/scripts', label: '脚本管理', icon: <FileCode size={18} /> },
  {
    type: 'group',
    label: '执行中心',
    icon: <ListTodo size={18} />,
    children: [
      { path: '/tasks', label: '任务管理', icon: <ListTodo size={16} /> },
      { path: '/reports', label: '报告管理', icon: <FileText size={16} /> },
    ],
  },
  { type: 'single', path: '/settings', label: '模型配置', icon: <Settings size={18} /> },
];

export function Sidebar() {
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
      className={`fixed left-0 top-0 h-full bg-white border-r border-[#e2e8f0] transition-all duration-200 z-50 ${
        collapsed ? 'w-14' : 'w-56'
      }`}
    >
      {/* Logo */}
      <div className="h-14 flex items-center justify-between px-3 border-b border-[#e2e8f0]">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#165DFF] flex items-center justify-center">
              <Bot size={18} className="text-white" />
            </div>
            <div>
              <span className="font-semibold text-[#0f172a] text-sm">Mobile Agent</span>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 rounded-lg bg-[#165DFF] flex items-center justify-center mx-auto">
            <Bot size={18} className="text-white" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="p-2 space-y-0.5">
        {navEntries.map((entry) => {
          if (entry.type === 'single') {
            return (
              <NavLink
                key={entry.path}
                to={entry.path}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-[#e8f0fe] text-[#165DFF]'
                      : 'text-[#475569] hover:bg-[#f1f5f9] hover:text-[#0f172a]'
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
                className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition-all duration-200 ${
                  collapsed ? 'justify-center' : ''
                } text-[#475569] hover:bg-[#f1f5f9] hover:text-[#0f172a]`}
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
                <div className="ml-1.5 mt-0.5 space-y-0.5 pl-4 border-l border-[#e2e8f0]">
                  {entry.children.map((child) => (
                    <NavLink
                      key={child.path}
                      to={child.path}
                      className={({ isActive }) =>
                        `flex items-center gap-2 px-2.5 py-1.5 rounded-lg transition-all duration-200 ${
                          isActive
                            ? 'bg-[#e8f0fe] text-[#165DFF]'
                            : 'text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a]'
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

      {/* Toggle Button */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
        className="absolute -right-3 top-16 w-6 h-6 bg-white rounded-full flex items-center justify-center text-[#94a3b8] hover:text-[#165DFF] transition-colors border border-[#e2e8f0]"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Version */}
      {!collapsed && (
        <div className="absolute bottom-4 left-4 right-4 text-xs text-[#94a3b8] text-center">
          v1.0.0
        </div>
      )}
    </aside>
  );
}