import { Package, Upload, Trash2, FolderOpen, AlertCircle, CheckCircle, Loader2, X } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';
import { useApkStore } from '../../stores/apkStore';

export function ApkPage() {
  const { apks, loading, uploading, error, success, fetchApks, uploadApk, deleteApk, batchDeleteApks, clearMessages } = useApkStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchApks();
  }, [fetchApks]);

  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => clearMessages(), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success, clearMessages]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.toLowerCase().endsWith('.apk')) {
      uploadApk(file);
    } else if (file) {
      alert('请选择APK文件');
    }
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === apks.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(apks.map(a => a.id)));
    }
  };

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) return;
    batchDeleteApks(Array.from(selectedIds));
    setSelectedIds(new Set());
    setBatchMode(false);
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '未知';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Package className="w-6 h-6 text-indigo-400" />
            APK管理
          </h1>
          <p className="text-[#94a3b8] mt-1">管理您的测试APK文件</p>
        </div>
        <div className="flex items-center gap-2">
          {batchMode ? (
            <>
              <span className="text-[#94a3b8] text-sm">{selectedIds.size} 已选择</span>
              <button
                onClick={handleBatchDelete}
                disabled={selectedIds.size === 0}
                title="批量删除"
                className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-red-800 text-white rounded-lg flex items-center gap-2 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => { setBatchMode(false); setSelectedIds(new Set()); }}
                className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors"
              >
                <X className="w-4 h-4" />
                取消
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setBatchMode(true)}
                title="批量删除"
                className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white rounded-lg flex items-center gap-2 transition-colors"
              >
                {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {uploading ? '上传中...' : '上传APK'}
              </button>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".apk"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-300">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-900/30 border border-green-500/30 rounded-lg flex items-center gap-2 text-green-300">
          <CheckCircle className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* APK List */}
      {loading ? (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-8 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mr-2" />
          <span className="text-[#94a3b8]">加载中...</span>
        </div>
      ) : apks.length === 0 ? (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="text-center py-20">
            <FolderOpen className="w-16 h-16 text-[#475569] mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无APK文件</h3>
            <p className="text-[#64748b]">上传您的第一个APK文件开始测试</p>
          </div>
        </div>
      ) : (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#0f172a] border-b border-[#334155]">
                <tr>
                  {batchMode && (
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={apks.length > 0 && selectedIds.size === apks.length}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 accent-indigo-500"
                      />
                    </th>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    APK文件名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    包名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    版本号
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    大小
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    上传时间
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#334155]">
                {apks.map((apk) => (
                  <tr key={apk.id} className="hover:bg-[#0f172a]/50">
                    {batchMode && (
                      <td className="px-4 py-4">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(apk.id)}
                          onChange={() => toggleSelect(apk.id)}
                          className="w-4 h-4 accent-indigo-500"
                        />
                      </td>
                    )}
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white font-medium">
                      {apk.original_filename || apk.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8] font-mono">
                      {apk.package_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {apk.version || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {formatFileSize(apk.file_size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
                      {formatDate(apk.upload_time)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {!batchMode && (
                        <button
                          onClick={() => deleteApk(apk.id)}
                          title="删除"
                          className="text-red-400 hover:text-red-300 flex items-center gap-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}