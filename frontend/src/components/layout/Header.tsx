import { User, Bell } from 'lucide-react';

export function Header() {
  return (
    <header className="h-14 bg-white border-b border-[#e2e8f0] flex items-center justify-between px-4 fixed top-0 right-0 left-56 z-40">
      {/* Left: Title */}
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-[#0f172a]">Mobile Agent</h1>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <button className="p-2 text-[#64748b] hover:text-[#0f172a] hover:bg-[#f1f5f9] rounded-lg transition-all duration-200" title="通知">
          <Bell size={18} />
        </button>
        <div className="w-8 h-8 rounded-full bg-[#165DFF] flex items-center justify-center">
          <User size={16} className="text-white" />
        </div>
      </div>
    </header>
  );
}