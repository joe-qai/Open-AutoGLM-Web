import { Package, Upload, Trash2, FolderOpen, AlertCircle, CheckCircle, Loader2, X } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';
import { useApkStore } from '../../stores/apkStore';
import { getAppName } from '../../config/apps';

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
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-[#0f172a] flex items-center gap-2">
            <Package className="w-5 h-5 text-[#165DFF]" />
            APK管理
          </h1>
          <p className="text-[#64748b] text-sm mt-1">管理您的测试APK文件</p>
        </div>
        <div className="flex items-center gap-2">
          {batchMode ? (
            <>
              <span className="text-[#64748b] text-sm">{selectedIds.size} 已选择</span>
              <button
                onClick={handleBatchDelete}
                disabled={selectedIds.size === 0}
                title="批量删除"
                className="px-4 py-2 bg-[#ef4444] hover:bg-[#dc2626] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-all duration-200"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => { setBatchMode(false); setSelectedIds(new Set()); }}
                className="px-4 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] rounded-lg flex items-center gap-2 transition-all duration-200"
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
                className="px-4 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] rounded-lg flex items-center gap-2 transition-all duration-200"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-all duration-200"
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
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-[#dc2626]">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-[#16a34a]">
          <CheckCircle className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Select All Header */}
      {!loading && apks.length > 0 && batchMode && (
        <div className="flex items-center gap-3 mb-3">
          <button onClick={toggleSelectAll} className="text-[#94a3b8] hover:text-[#165DFF] transition-colors duration-200">
            {selectedIds.size === apks.length ? (
              <CheckCircle className="w-4 h-4 text-[#165DFF]" />
            ) : (
              <div className="w-4 h-4 rounded border-2 border-[#cbd5e1]" />
            )}
          </button>
          <span className="text-[#64748b] text-xs">全选 ({apks.length})</span>
        </div>
      )}

      {/* APK Cards */}
      {loading ? (
        <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-lg p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-[#165DFF] animate-spin mr-2" />
          <span className="text-[#64748b]">加载中...</span>
        </div>
      ) : apks.length === 0 ? (
        <div className="text-center py-16 bg-[#f8fafc] border border-[#e2e8f0] rounded-lg">
          <FolderOpen className="w-12 h-12 text-[#94a3b8] mx-auto mb-3" />
          <h3 className="text-[#0f172a] text-base font-medium mb-1.5">暂无APK文件</h3>
          <p className="text-[#64748b] text-sm">上传您的第一个APK文件开始测试</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {apks.map((apk) => (
            <div
              key={apk.id}
              className="bg-white border border-[#e2e8f0] rounded-lg p-4 hover:border-[#165DFF] hover:shadow-md transition-all duration-200"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start gap-3">
                  {batchMode && (
                    <button
                      onClick={() => toggleSelect(apk.id)}
                      className="mt-1 text-[#94a3b8] hover:text-[#165DFF] transition-colors duration-200"
                    >
                      {selectedIds.has(apk.id) ? (
                        <CheckCircle className="w-4 h-4 text-[#165DFF]" />
                      ) : (
                        <div className="w-4 h-4 rounded border-2 border-[#cbd5e1]" />
                      )}
                    </button>
                  )}
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg flex items-center justify-center shrink-0 border border-blue-200">
                    <Package className="w-5 h-5 text-[#165DFF]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-[#0f172a] font-medium text-sm truncate">
                      {apk.original_filename || apk.name}
                    </h3>
                    {apk.package_name && (
                      <p className="text-[#64748b] text-xs font-mono truncate mt-0.5">
                        {getAppName(apk.package_name) || apk.package_name}
                      </p>
                    )}
                  </div>
                </div>
                {!batchMode && (
                  <button
                    onClick={() => deleteApk(apk.id)}
                    className="p-1.5 text-[#94a3b8] hover:text-[#ef4444] hover:bg-red-50 rounded-lg transition-all duration-200"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[#94a3b8]">版本号</span>
                  <span className="text-[#64748b]">{apk.version || '-'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#94a3b8]">文件大小</span>
                  <span className="text-[#64748b]">{formatFileSize(apk.file_size)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#94a3b8]">上传时间</span>
                  <span className="text-[#64748b]">{formatDate(apk.upload_time)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}