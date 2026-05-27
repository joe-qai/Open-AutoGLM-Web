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

      {/* Select All Header */}
      {!loading && apks.length > 0 && batchMode && (
        <div className="flex items-center gap-4 mb-4">
          <button onClick={toggleSelectAll} className="text-slate-400 hover:text-white transition-colors">
            {selectedIds.size === apks.length ? (
              <div className="w-5 h-5 rounded border-2 border-indigo-400 bg-indigo-400 flex items-center justify-center">
                <CheckCircle className="w-3 h-3 text-white" />
              </div>
            ) : (
              <div className="w-5 h-5 rounded border-2 border-slate-500" />
            )}
          </button>
          <span className="text-slate-400 text-sm">全选 ({apks.length})</span>
        </div>
      )}

      {/* APK Cards */}
      {loading ? (
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm border border-slate-700/30 rounded-2xl p-8 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mr-2" />
          <span className="text-slate-400">加载中...</span>
        </div>
      ) : apks.length === 0 ? (
        <div className="text-center py-20 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm border border-slate-700/30 rounded-2xl">
          <FolderOpen className="w-16 h-16 text-slate-500 mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无APK文件</h3>
          <p className="text-slate-400">上传您的第一个APK文件开始测试</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {apks.map((apk) => (
            <div
              key={apk.id}
              className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 hover:shadow-xl hover:shadow-indigo-500/5 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-3">
                  {batchMode && (
                    <button
                      onClick={() => toggleSelect(apk.id)}
                      className="mt-1 text-slate-400 hover:text-white transition-colors"
                    >
                      {selectedIds.has(apk.id) ? (
                        <div className="w-5 h-5 rounded border-2 border-indigo-400 bg-indigo-400 flex items-center justify-center">
                          <CheckCircle className="w-3 h-3 text-white" />
                        </div>
                      ) : (
                        <div className="w-5 h-5 rounded border-2 border-slate-500" />
                      )}
                    </button>
                  )}
                  <div className="w-12 h-12 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-xl flex items-center justify-center shrink-0 border border-green-500/30">
                    <Package className="w-6 h-6 text-green-400" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-lg truncate max-w-xs">
                      {apk.original_filename || apk.name}
                    </h3>
                    {apk.package_name && (
                      <p className="text-slate-400 text-xs font-mono truncate">{apk.package_name}</p>
                    )}
                  </div>
                </div>
                {!batchMode && (
                  <button
                    onClick={() => deleteApk(apk.id)}
                    className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-200"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">版本号</span>
                  <span className="text-slate-300">{apk.version || '-'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">文件大小</span>
                  <span className="text-slate-300">{formatFileSize(apk.file_size)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">上传时间</span>
                  <span className="text-slate-300">{formatDate(apk.upload_time)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}