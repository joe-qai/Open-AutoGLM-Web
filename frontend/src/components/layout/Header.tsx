import { User } from 'lucide-react';

export function Header() {
  return (
    <header className="h-16 bg-[#1e293b] border-b border-[#334155] flex items-center justify-between px-6 fixed top-0 right-0 left-60 z-40">
      {/* Left: Title */}
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-white">LOCKIN Agent Platform</h1>
      </div>

      {/* Right: User profile only */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <User size={16} className="text-white" />
        </div>
        <div className="hidden md:block">
          <p className="text-sm font-medium text-white">管理员</p>
          <p className="text-xs text-[#64748b]">admin@lockin.com</p>
        </div>
      </div>
    </header>
  );
}